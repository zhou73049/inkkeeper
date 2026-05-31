from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日', '每天']


class ScheduledJob(db.Model):
    __tablename__ = 'scheduled_jobs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default='喷头保养')
    enabled = db.Column(db.Boolean, default=True)
    images_per_run = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'enabled': self.enabled,
            'images_per_run': self.images_per_run,
            'times': [t.to_dict() for t in self.times],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ScheduledTime(db.Model):
    __tablename__ = 'scheduled_times'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scheduled_jobs.id'), nullable=False)
    day_of_week = db.Column(db.Integer, default=7)
    hour = db.Column(db.Integer, default=9)
    minute = db.Column(db.Integer, default=0)
    last_run = db.Column(db.DateTime, nullable=True)
    job = db.relationship('ScheduledJob',
                          backref=db.backref('times', lazy=True, cascade='all, delete-orphan'))

    @property
    def day_name(self):
        return DAY_NAMES[self.day_of_week] if 0 <= self.day_of_week < len(DAY_NAMES) else '?'

    @property
    def time_str(self):
        return f'{self.hour:02d}:{self.minute:02d}'

    def to_dict(self):
        return {
            'id': self.id, 'job_id': self.job_id,
            'day_of_week': self.day_of_week, 'day_name': self.day_name,
            'hour': self.hour, 'minute': self.minute, 'time_str': self.time_str,
            'last_run': self.last_run.isoformat() if self.last_run else None,
        }


class UploadedImage(db.Model):
    __tablename__ = 'uploaded_images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    print_count = db.Column(db.Integer, default=0)
    last_printed = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    tag = db.Column(db.String(50), default='保养图')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'filename': self.filename,
            'original_name': self.original_name, 'file_size': self.file_size,
            'width': self.width, 'height': self.height,
            'print_count': self.print_count,
            'last_printed': self.last_printed.isoformat() if self.last_printed else None,
            'is_active': self.is_active, 'tag': self.tag,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class PrintLog(db.Model):
    __tablename__ = 'print_logs'
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('uploaded_images.id'), nullable=True)
    image_name = db.Column(db.String(255), default='')
    job_id = db.Column(db.Integer, db.ForeignKey('scheduled_jobs.id'), nullable=True)
    status = db.Column(db.String(20), default='success')
    message = db.Column(db.Text, default='')
    method = db.Column(db.String(50), default='auto')
    printed_at = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.relationship('UploadedImage', backref='print_logs', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'image_id': self.image_id,
            'image_name': self.image_name, 'job_id': self.job_id,
            'status': self.status, 'message': self.message,
            'method': self.method,
            'printed_at': self.printed_at.isoformat() if self.printed_at else None,
        }
