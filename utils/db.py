import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, PrimaryKeyConstraint, text
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from pandas import DataFrame
from datetime import datetime

# DB file directory in Documents
documents_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'Screen_Time_Tracker')
os.makedirs(documents_dir, exist_ok=True)
DB_PATH = f'sqlite:///{documents_dir}/screentime.db'

Base = declarative_base()
class PrintableBase(Base):
    __abstract__ = True
    def __str__(self):
        return f"{self.__class__.__name__}({', '.join(f'{k}={v}' for k, v in self.__dict__.items() if not k.startswith('_'))})"

class App(PrintableBase):
    __tablename__ = 'Apps'
    id = Column(Integer, primary_key=True)
    app_name = Column(String, unique=True)
    file_location = Column(String, nullable=False)
    icon_location = Column(String, nullable=True)

class Record(PrintableBase):
    __tablename__ = 'Records'
    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, nullable=False)
    app_id = Column(Integer, ForeignKey('Apps.id'), nullable=False)
    app = relationship("App")

class HourlyRecords(PrintableBase):
    __tablename__ = 'HourlyRecords'
    datetime = Column(DateTime, nullable=False)
    app_id = Column(Integer, ForeignKey('Apps.id'), nullable=False)
    duration = Column(Integer, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('datetime', 'app_id'),
    )
    app = relationship("App")

def create_db(readonly: bool=False) -> Session:
    if readonly:
        engine = create_engine(DB_PATH + '?mode=ro', uri=True)
    else:
        engine = create_engine(DB_PATH)
    PrintableBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    db = session()
    return db

def get_all_records() -> DataFrame:
    session = create_db()
    records = session.query(HourlyRecords).all()
    session.close()
    df = DataFrame([record.__dict__ for record in records])
    df.rename({'duration': 'usage'})
    return df
def get_all_apps_names() -> list[str]:
    session = create_db()
    apps = session.query(App).all()
    session.close()
    return [app.app_name for app in apps]

def add_record(app_name: str, app_path: str, timestamp: int) -> None:
    # Create a database session
    session = create_db()
    # Check if the app is already in the database
    app = session.query(App).filter_by(app_name=app_name).first()
    if not app:
        # If not, create a new app entry
        app = App(app_name=app_name, file_location=app_path)
        session.add(app)
    # Create a new record entry
    record = Record(timestamp=timestamp, app=app)
    session.add(record)
    session.commit()
    session.close()

def update_app_icon(app_name: str, icon_path: str, file_location: str='') -> None:
    session = create_db()
    app = session.query(App).filter_by(app_name=app_name).first()
    if not app:
        app = App(app_name=app_name, icon_location=icon_path, file_location=file_location or 'Unknown')
        session.add(app)
    elif icon_path and icon_path != 'Unknown' and os.path.exists(icon_path):
        app.icon_location = icon_path
    session.commit()
    session.close()

def is_transformation_needed() -> int:
    """
    Checks if transformation is needed or not
    """
    session = create_db()
    count = session.query(Record).count()
    session.close()
    # Check if there are more than 600 records (10 minutes)
    return max(0, 600 - count)

def transform_new_data() -> None:
    """
    Transform & migrate the existing data from Records table into HourlyRecords table
    """
    session = create_db()
    # Get all records from Records table
    records = session.query(Record).all()
    # group all records from Records table based on primary key
    hourly_records_dict = {}
    for record in records:
        app_id = record.app_id
        timestamp = record.timestamp
        hour = datetime.fromtimestamp(timestamp).replace(minute=0, second=0, microsecond=0)
        if (hour, app_id) not in hourly_records_dict:
            hourly_records_dict[(hour, app_id)] = 0
        hourly_records_dict[(hour, app_id)] += 1  # timestamp are in seconds
    # load into HourlyRecords (as upsert query)
    for (hour, app_id), duration in hourly_records_dict.items():
        existing_hourly_record = session.query(HourlyRecords).filter_by(datetime=hour, app_id=app_id).first()
        if existing_hourly_record:
            existing_hourly_record.duration += duration
        else:
            new_hourly_record = HourlyRecords(datetime=hour, app_id=app_id, duration=duration)
            session.add(new_hourly_record)
    # truncate Records
    session.query(Record).delete()
    # commit
    session.commit()
    session.close()
    # refresh
    engine = create_engine(DB_PATH)
    with engine.connect() as connection:
        connection.execute(text("VACUUM"))
