import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, send_from_directory)
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
from config import Config
from models import db, ScheduledJob, ScheduledTime, UploadedImage, PrintLog
from printer import print_image, check_printer_status, list_cups_printers
from scheduler import PrintScheduler

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('inkkeeper')

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app()
db.init_app(app)
ps = PrintScheduler(app)
ALLOWED = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp'}


def ok_ext(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED


@app.route('/')
def index():
    jobs = ScheduledJob.query.order_by(ScheduledJob.created_at.desc()).all()
    recent_logs = PrintLog.query.order_by(PrintLog.printed_at.desc()).limit(20).all()
    image_count = UploadedImage.query.filter_by(is_active=True).count()
    total = db.session.query(db.func.sum(UploadedImage.print_count)).scalar() or 0
    printer = check_printer_status()
    today = datetime.now().replace(hour=0, minute=0, second=0)
    s_ok = PrintLog.query.filter(PrintLog.status == 'success', PrintLog.printed_at >= today).count()
    s_err = PrintLog.query.filter(PrintLog.status == 'error', PrintLog.printed_at >= today).count()
    return render_template('index.html', jobs=jobs, recent_logs=recent_logs,
        image_count=image_count, total_prints=total, printer=printer,
        success_today=s_ok, error_today=s_err)


@app.route('/images')
def images():
    p = request.args.get('page', 1, type=int)
    imgs = UploadedImage.query.order_by(UploadedImage.uploaded_at.desc()).paginate(page=p, per_page=24, error_out=False)
    return render_template('images.html', images=imgs)


@app.route('/upload', methods=['POST'])
def upload_image():
    if 'files' not in request.files:
        flash('请选择图片', 'warning')
        return redirect(url_for('images'))
    files = request.files.getlist('files')
    tag = request.form.get('tag', '保养图')
    cnt = 0
    for f in files:
        if f and f.filename and ok_ext(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            nm = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
            fp = Config.UPLOAD_FOLDER / nm
            f.save(str(fp))
            w, h, sz = None, None, fp.stat().st_size
            try:
                with PILImage.open(str(fp)) as im:
                    w, h = im.size
            except:
                pass
            db.session.add(UploadedImage(filename=nm,
                original_name=secure_filename(f.filename) or f.filename,
                filepath=str(fp), file_size=sz, width=w, height=h, tag=tag))
            cnt += 1
    db.session.commit()
    flash(f'上传 {cnt} 张图片', 'success')
    return redirect(url_for('images'))


@app.route('/image/<int:image_id>/delete', methods=['POST'])
def delete_image(image_id):
    img = UploadedImage.query.get_or_404(image_id)
    try:
        p = Path(img.filepath)
        if p.exists():
            p.unlink()
    except:
        pass
    db.session.delete(img)
    db.session.commit()
    flash(f'已删除: {img.original_name}', 'success')
    return redirect(url_for('images'))


@app.route('/image/<int:image_id>/toggle', methods=['POST'])
def toggle_image(image_id):
    img = UploadedImage.query.get_or_404(image_id)
    img.is_active = not img.is_active
    db.session.commit()
    flash(f'{"启用" if img.is_active else "禁用"}: {img.original_name}', 'info')
    return redirect(url_for('images'))


@app.route('/image/<int:image_id>/print', methods=['POST'])
def manual_print(image_id):
    img = UploadedImage.query.get_or_404(image_id)
    ok, msg = print_image(img.filepath, f'手动-{img.original_name}')
    db.session.add(PrintLog(image_id=img.id, image_name=img.original_name,
        status='success' if ok else 'error', message=msg, method='manual'))
    if ok:
        img.print_count += 1
        img.last_printed = datetime.now()
        flash(f'已发送: {img.original_name}', 'success')
    else:
        flash(f'打印失败: {msg}', 'danger')
    db.session.commit()
    return redirect(request.referrer or url_for('images'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(str(Config.UPLOAD_FOLDER), filename)


@app.route('/schedule')
def schedule():
    jobs = ScheduledJob.query.order_by(ScheduledJob.created_at.desc()).all()
    return render_template('schedule.html', jobs=jobs)


@app.route('/schedule/create', methods=['POST'])
def create_job():
    name = request.form.get('name', '喷头保养')
    images_per_run = request.form.get('images_per_run', 1, type=int)
    days = request.form.getlist('days', type=int)
    hour = request.form.get('hour', 9, type=int)
    minute = request.form.get('minute', 0, type=int)

    job = ScheduledJob(name=name, images_per_run=images_per_run)
    db.session.add(job)
    db.session.flush()

    if not days:
        days = [7]
    for d in days:
        db.session.add(ScheduledTime(job_id=job.id, day_of_week=d, hour=hour, minute=minute))

    db.session.commit()
    flash(f'已创建计划: {name}', 'success')
    return redirect(url_for('schedule'))


@app.route('/schedule/<int:job_id>/add_time', methods=['POST'])
def add_time(job_id):
    job = ScheduledJob.query.get_or_404(job_id)
    days = request.form.getlist('days', type=int)
    hour = request.form.get('hour', 9, type=int)
    minute = request.form.get('minute', 0, type=int)

    if not days:
        days = [7]
    for d in days:
        db.session.add(ScheduledTime(job_id=job.id, day_of_week=d, hour=hour, minute=minute))

    db.session.commit()
    flash(f'已添加 {len(days)} 个时间点', 'success')
    return redirect(url_for('schedule'))


@app.route('/schedule/time/<int:time_id>/delete', methods=['POST'])
def delete_time(time_id):
    t = ScheduledTime.query.get_or_404(time_id)
    job_id = t.job_id
    db.session.delete(t)
    db.session.commit()
    flash('已删除时间', 'success')
    return redirect(url_for('schedule'))


@app.route('/schedule/<int:job_id>/toggle', methods=['POST'])
def toggle_job(job_id):
    job = ScheduledJob.query.get_or_404(job_id)
    job.enabled = not job.enabled
    db.session.commit()
    flash(f'{"启用" if job.enabled else "暂停"}: {job.name}', 'info')
    return redirect(url_for('schedule'))


@app.route('/schedule/<int:job_id>/delete', methods=['POST'])
def delete_job(job_id):
    job = ScheduledJob.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash(f'已删除: {job.name}', 'success')
    return redirect(url_for('schedule'))


@app.route('/schedule/<int:job_id>/run', methods=['POST'])
def run_job_now(job_id):
    job = ScheduledJob.query.get_or_404(job_id)
    imgs = (UploadedImage.query.filter_by(is_active=True)
        .order_by(UploadedImage.last_printed.asc().nullsfirst())
        .limit(job.images_per_run).all())
    if not imgs:
        flash('没有可用图片', 'warning')
        return redirect(url_for('schedule'))
    ok_cnt = 0
    for img in imgs:
        ok, msg = print_image(img.filepath, f'手动-{job.name}')
        db.session.add(PrintLog(image_id=img.id, image_name=img.original_name,
            job_id=job.id, status='success' if ok else 'error',
            message=msg, method='manual'))
        if ok:
            img.print_count += 1
            img.last_printed = datetime.now()
            ok_cnt += 1
    db.session.commit()
    flash(f'[{job.name}] {ok_cnt}/{len(imgs)} 完成', 'success')
    return redirect(url_for('schedule'))


@app.route('/logs')
def logs():
    p = request.args.get('page', 1, type=int)
    sf = request.args.get('status', '')
    q = PrintLog.query
    if sf:
        q = q.filter_by(status=sf)
    all_logs = q.order_by(PrintLog.printed_at.desc()).paginate(page=p, per_page=50, error_out=False)
    return render_template('logs.html', logs=all_logs, status_filter=sf)


@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    PrintLog.query.delete()
    db.session.commit()
    flash('已清空日志', 'success')
    return redirect(url_for('logs'))


@app.route('/settings')
def settings():
    printer = check_printer_status()
    pl = list_cups_printers()
    cfg = {'PRINTER_NAME': Config.PRINTER_NAME, 'PRINTER_IP': Config.PRINTER_IP,
        'PRINTER_CONNECTION': Config.PRINTER_CONNECTION, 'PRINT_SCRIPT': Config.PRINT_SCRIPT,
        'TZ': Config.SCHEDULER_TIMEZONE}
    return render_template('settings.html', printer=printer, printers_list=pl, config=cfg)


@app.route('/api/status')
def api_status():
    return jsonify({
        'printer': check_printer_status(),
        'active_jobs': ScheduledJob.query.filter_by(enabled=True).count(),
        'active_images': UploadedImage.query.filter_by(is_active=True).count(),
        'scheduler_running': ps.scheduler.running})


def init_db():
    with app.app_context():
        db.create_all()
        logger.info('数据库初始化完成')


init_db()
ps.start()

if __name__ == '__main__':
    init_db()
    ps.start()
    logger.info('InkKeeper 启动完成')
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        ps.stop()
