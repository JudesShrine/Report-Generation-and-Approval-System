from fastapi.responses import FileResponse
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    create_engine
)
from sqlalchemy.orm import (
    Session,
    sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import inspect, text
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import secrets
from fastapi import Header


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Report Generation and Approval System",
    description="Backend API for College Report Generation and Approval System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

APP_DIR = Path(__file__).resolve().parent


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = "sqlite:///./report_system.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Opaque, server-side login sessions keep approval authorization out of
# client-controlled role fields. Sessions expire when the API process restarts.
active_sessions: dict[str, int] = {}


# ============================================================
# DATABASE MODELS
# ============================================================

# -------------------------
# USER TABLE
# -------------------------

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        default="student",
        nullable=False
    )

    name = Column(String, nullable=True)
    college_code = Column(String, nullable=True)
    authorization_code = Column(String, nullable=True)


# -------------------------
# REPORT TABLE
# -------------------------

class Report(Base):

    __tablename__ = "reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String,
        index=True,
        nullable=False
    )

    department = Column(
        String,
        index=True,
        nullable=False
    )

    report_type = Column(
        String,
        index=True,
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=False
    )

    status = Column(
        String,
        default="Pending",
        index=True
    )

    approver_comment = Column(
        Text,
        nullable=True
    )

    report_date = Column(String, nullable=True)
    submitted_by = Column(String, nullable=True)
    submitted_role = Column(String, nullable=True)
    attachment_id = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_type = Column(String, nullable=True)


# Create database tables

Base.metadata.create_all(bind=engine)

# Add fields used by the current frontend when upgrading an existing database.
with engine.begin() as connection:
    existing_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    for column_name in ("name", "college_code", "authorization_code"):
        if column_name not in existing_columns:
            connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} VARCHAR"))
    existing_report_columns = {column["name"] for column in inspect(engine).get_columns("reports")}
    for column_name in ("report_date", "submitted_by", "submitted_role", "attachment_id", "file_name", "file_type"):
        if column_name not in existing_report_columns:
            connection.execute(text(f"ALTER TABLE reports ADD COLUMN {column_name} VARCHAR"))


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================


# -------------------------
# USER CREATE
# -------------------------

class UserCreate(BaseModel):

    username: str

    email: str

    password: str

    role: str
    name: str
    college_code: str
    authorization_code: str


# -------------------------
# USER RESPONSE
# -------------------------

class UserResponse(BaseModel):

    id: int

    username: str

    email: str

    role: str
    name: Optional[str] = None
    college_code: Optional[str] = None

    class Config:
        orm_mode = True


# -------------------------
# LOGIN
# -------------------------

class LoginRequest(BaseModel):

    username: str

    password: str
    role: str
    college_code: str
    authorization_code: str


# -------------------------
# REPORT CREATE
# -------------------------

class ReportCreate(BaseModel):

    title: str

    department: str

    report_type: str

    description: str

    created_by: int
    report_date: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_role: Optional[str] = None
    attachment_id: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None


# -------------------------
# REPORT UPDATE
# -------------------------

class ReportUpdate(BaseModel):

    title: str

    department: str

    report_type: str

    description: str


# -------------------------
# REPORT RESPONSE
# -------------------------

class ReportResponse(BaseModel):

    id: int

    title: str

    department: str

    report_type: str

    description: str

    created_by: int

    status: str

    approver_comment: Optional[str] = None
    report_date: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_role: Optional[str] = None
    attachment_id: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None

    class Config:
        orm_mode = True


# -------------------------
# APPROVAL REQUEST
# -------------------------

class ApprovalRequest(BaseModel):

    status: str

    approver_comment: Optional[str] = None


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db)
):
    scheme, _, token = (authorization or "").partition(" ")
    user_id = active_sessions.get(token) if scheme.lower() == "bearer" else None
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in again.")
    return user


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return FileResponse(APP_DIR / "index.html")


@app.get("/index.html")
def login_page():
    return FileResponse(APP_DIR / "index.html")


@app.get("/home.html")
def dashboard_page():
    return FileResponse(APP_DIR / "home.html")


# ============================================================
# USER APIs
# ============================================================


# -------------------------
# CREATE USER
# -------------------------

@app.post(
    "/users/create/",
    response_model=UserResponse
)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    # Check username

    existing_username = db.query(User).filter(
        User.username == user.username
    ).first()

    if existing_username:

        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )


    # Check email

    existing_email = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_email:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    # Check role

    allowed_roles = [
        "Admin",
        "Staff",
        "HOD",
        "Principal",
        "Authorized Person"
    ]

    if user.role not in allowed_roles:

        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    authorization_codes = {
        "Admin": "ADMIN2026",
        "Staff": "STAFF2026",
        "HOD": "HOD2026",
        "Principal": "PRINCIPAL2026",
        "Authorized Person": "AUTH2026"
    }
    if len(user.name.strip()) < 3 or len(user.college_code.strip()) < 4:
        raise HTTPException(status_code=400, detail="Please enter a valid name and college code.")
    if user.authorization_code.strip().upper() != authorization_codes[user.role]:
        raise HTTPException(status_code=400, detail="Invalid authorization code for selected role.")


    db_user = User(

        username=user.username,

        email=user.email,

        password=user.password,

        role=user.role,
        name=user.name.strip(),
        college_code=user.college_code.strip().upper(),
        authorization_code=user.authorization_code.strip().upper()

    )


    db.add(db_user)

    db.commit()

    db.refresh(db_user)

    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role,
        "name": db_user.name,
        "college_code": db_user.college_code
    }


# -------------------------
# GET ALL USERS
# -------------------------

@app.get(
    "/users/",
    response_model=list[UserResponse]
)
def get_users(
    db: Session = Depends(get_db)
):

    users = db.query(User).all()

    return users


# -------------------------
# GET ONE USER
# -------------------------

@app.get(
    "/users/{user_id}",
    response_model=UserResponse
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()


    if user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )


    return user


# ============================================================
# LOGIN
# ============================================================

@app.post("/users/login/")
def login_user(
    login: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.email == login.username.lower()).first()


    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )


    if (user.password != login.password
            or user.role != login.role
            or user.college_code != login.college_code.upper()
            or user.authorization_code != login.authorization_code.upper()):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )


    return {

        "message": "Login successful",

        "user_id": user.id,

        "username": user.username,

        "email": user.email,

        "role": user.role,
        "name": user.name or user.username,
        "college_code": user.college_code or "",
        "access_token": _create_session(user)

    }


def _create_session(user: User) -> str:
    token = secrets.token_urlsafe(32)
    active_sessions[token] = user.id
    return token


# ============================================================
# REPORT APIs
# ============================================================


# -------------------------
# CREATE REPORT
# -------------------------

@app.post(
    "/reports/",
    response_model=ReportResponse
)
def create_report(
    report: ReportCreate,
    db: Session = Depends(get_db)
):

    # Check user

    user = db.query(User).filter(
        User.id == report.created_by
    ).first()


    if user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )


    # Create report

    db_report = Report(

        title=report.title,

        department=report.department,

        report_type=report.report_type,

        description=report.description,

        created_by=report.created_by,

        report_date=report.report_date,
        submitted_by=report.submitted_by,
        submitted_role=report.submitted_role,
        attachment_id=report.attachment_id,
        file_name=report.file_name,
        file_type=report.file_type,

        status="Pending"

    )


    db.add(db_report)

    db.commit()

    db.refresh(db_report)


    return db_report


# -------------------------
# GET ALL REPORTS
# -------------------------

@app.get(
    "/reports/",
    response_model=list[ReportResponse]
)
def get_reports(
    db: Session = Depends(get_db)
):

    reports = db.query(Report).order_by(
        Report.id.desc()
    ).all()


    return reports


# -------------------------
# GET ONE REPORT
# -------------------------

@app.get(
    "/reports/{report_id}",
    response_model=ReportResponse
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):

    report = db.query(Report).filter(
        Report.id == report_id
    ).first()


    if report is None:

        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )


    return report


# ============================================================
# GET REPORTS CREATED BY USER
# ============================================================

@app.get(
    "/reports/user/{user_id}",
    response_model=list[ReportResponse]
)
def get_user_reports(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()


    if user is None:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )


    reports = db.query(Report).filter(
        Report.created_by == user_id
    ).order_by(
        Report.id.desc()
    ).all()


    return reports


# ============================================================
# GET PENDING REPORTS
# ============================================================

@app.get(
    "/reports/status/pending",
    response_model=list[ReportResponse]
)
def get_pending_reports(
    db: Session = Depends(get_db)
):

    reports = db.query(Report).filter(
        Report.status == "Pending"
    ).order_by(
        Report.id.desc()
    ).all()


    return reports


# ============================================================
# GET APPROVED REPORTS
# ============================================================

@app.get(
    "/reports/status/approved",
    response_model=list[ReportResponse]
)
def get_approved_reports(
    db: Session = Depends(get_db)
):

    reports = db.query(Report).filter(
        Report.status == "Approved"
    ).order_by(
        Report.id.desc()
    ).all()


    return reports


# ============================================================
# GET REJECTED REPORTS
# ============================================================

@app.get(
    "/reports/status/rejected",
    response_model=list[ReportResponse]
)
def get_rejected_reports(
    db: Session = Depends(get_db)
):

    reports = db.query(Report).filter(
        Report.status == "Rejected"
    ).order_by(
        Report.id.desc()
    ).all()


    return reports


# ============================================================
# UPDATE REPORT
# ============================================================

@app.put(
    "/reports/{report_id}",
    response_model=ReportResponse
)
def update_report(
    report_id: int,
    report_data: ReportUpdate,
    db: Session = Depends(get_db)
):

    report = db.query(Report).filter(
        Report.id == report_id
    ).first()


    if report is None:

        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )


    # Update details

    report.title = report_data.title

    report.department = report_data.department

    report.report_type = report_data.report_type

    report.description = report_data.description


    db.commit()

    db.refresh(report)


    return report


# ============================================================
# APPROVE / REJECT REPORT
# ============================================================

@app.put(
    "/reports/{report_id}/approval",
    response_model=ReportResponse
)
def approve_or_reject_report(
    report_id: int,
    approval: ApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if current_user.role != "Authorized Person":
        raise HTTPException(status_code=403, detail="Only the Authorized Person can approve or reject files.")

    report = db.query(Report).filter(
        Report.id == report_id
    ).first()


    if report is None:

        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )


    # Check status

    allowed_status = ["Approved", "Rejected"]


    if approval.status not in allowed_status:

        raise HTTPException(
            status_code=400,
            detail="Invalid approval status"
        )

    if report.status != "Pending":
        raise HTTPException(status_code=409, detail="This report has already been reviewed.")


    # Rejection requires comment

    if (
        approval.status == "Rejected"
        and not approval.approver_comment
    ):

        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required"
        )


    report.status = approval.status

    report.approver_comment = approval.approver_comment


    db.commit()

    db.refresh(report)


    return report


# ============================================================
# DELETE REPORT
# ============================================================

@app.delete(
    "/reports/{report_id}"
)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db)
):

    report = db.query(Report).filter(
        Report.id == report_id
    ).first()


    if report is None:

        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )


    db.delete(report)

    db.commit()


    return {

        "message": "Report deleted successfully",

        "report_id": report_id

    }


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@app.get("/dashboard/")
def dashboard(
    db: Session = Depends(get_db)
):

    total = db.query(Report).count()


    pending = db.query(Report).filter(
        Report.status == "Pending"
    ).count()


    approved = db.query(Report).filter(
        Report.status == "Approved"
    ).count()


    rejected = db.query(Report).filter(
        Report.status == "Rejected"
    ).count()


    users = db.query(User).count()


    return {

        "total_users": users,

        "total_reports": total,

        "pending_reports": pending,

        "approved_reports": approved,

        "rejected_reports": rejected

    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
