import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from models import db, ScheduledJob, UploadedImage, PrintLog
from printer import print_image

logger = logging.getLogger('inkkeeper.scheduler')


class PrintScheduler:
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler(
            timezone=app.config.get('SCHEDULER_TIMEZONE', 'Asia/Shanghai'))

    def start(self):
        self.scheduler.add_job(
            func=self._check_and_print,
            trigger=IntervalTrigger(seconds=30),
            id='print_check_loop', name='定时打印检查', replace_existing=True)
        self.scheduler.start()
        logger.info('调度器已启动')

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info('调度器已停止')

    def _check_and_print(self):
        with self.app.app_context():
            now = datetime.now()
            for job in ScheduledJob.query.filter_by(enabled=True).all():
                for t in job.times:
                    if self._matches(t, now):
                        self._run(job, t, now)

    def _matches(self, t, now):
        if t.day_of_week != 7 and t.day_of_week != now.weekday():
            return False
        if t.hour != now.hour or t.minute != now.minute:
            return False
        if t.last_run and (now - t.last_run).total_seconds() < 120:
            return False
        return True

    def _run(self, job, ts, now):
        images = (UploadedImage.query.filter_by(is_active=True)
                  .order_by(UploadedImage.last_printed.asc().nullsfirst())
                  .limit(job.images_per_run).all())
        if not images:
            return
        ok_n = 0
        for img in images:
            ok, msg = print_image(img.filepath, f'InkKeeper-{job.name}')
            db.session.add(PrintLog(
                image_id=img.id, image_name=img.original_name,
                job_id=job.id, status='success' if ok else 'error',
                message=msg, method='auto'))
            if ok:
                img.print_count += 1
                img.last_printed = now
                ok_n += 1
        ts.last_run = now
        db.session.commit()
        logger.info(f'[{job.name}] {ts.day_name} {ts.time_str} -> {ok_n}/{len(images)}')
