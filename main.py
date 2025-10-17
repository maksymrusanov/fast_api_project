
from os import getenv
from typing import Annotated, Optional
from contextlib import asynccontextmanager
import time

# FastAPI and utilities
from fastapi import Depends, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# SQLModel and SQLAlchemy for Database
from sqlmodel import Field, Session, SQLModel, create_engine, select, text
# Used for robust DB creation
from sqlalchemy.exc import OperationalError, ProgrammingError


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    text: str | None = Field(default=None, index=True)
    status: bool = Field(index=True, default=False)


DB_HOST = getenv("DB_HOST", "127.0.0.1")
DB_PORT = getenv("DB_PORT", "3306")
DB_USER = getenv("DB_USER", "root")
DB_PASSWORD = getenv("DB_PASSWORD", "")
DB_NAME = getenv("DB_NAME", "mydb")

SERVER_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/"
DATABASE_URL = f"{SERVER_URL}{DB_NAME}"


SERVER_URL = f"mysql+pymysql://root:{DB_PASSWORD}@db:{DB_PORT}/"
DATABASE_URL = f"{SERVER_URL}{DB_NAME}"


def create_db_and_tables():
    retries = 10
    for i in range(retries):
        try:
            SQLModel.metadata.create_all(engine)
            print("Tables created successfully")
            break
        except OperationalError:
            print(f"DB not ready, retry {i+1}/{retries}")
            time.sleep(2)


# --- ENGINE AND DEPENDENCIES ---
connect_args = {"check_same_thread": False}
# This main engine is configured with the full URL
engine = create_engine(DATABASE_URL)


def get_session():
    """Dependency to provide a database session."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

# --- FASTAPI LIFESPAN AND APP CREATION ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs once when the application starts up.
    It guarantees that the DB and tables are ready before requests are served.
    """

    create_db_and_tables()
    yield  # Application continues serving requests after this point


# create your app
app = FastAPI(lifespan=lifespan)
# Static files and templates setup
templates = Jinja2Templates(directory="templates")


# --- APPLICATION ROUTES ---

@app.get("/", response_class=HTMLResponse)
def main_page(request: Request, session: SessionDep):
    tasks = session.exec(select(Task)).all()
    # Handle the case where the table might still be initializing/missing
    if not tasks and not session.exec(select(Task).limit(1)).first():
        print("Database seems empty or table just created.")

    return templates.TemplateResponse(
        "main.html",
        {"request": request, "tasks": tasks}
    )


@app.get("/create", response_class=HTMLResponse)
def create_task(request: Request):
    return templates.TemplateResponse(
        "create_task.html", {'request': request})


@app.post("/create")
def create_page(session: SessionDep, title: str = Form(...), text: str = Form(...), status: bool = Form(default=False)):
    task = Task(title=title, text=text, status=status)
    session.add(task)
    session.commit()
    session.refresh(task)
    return RedirectResponse(url="/", status_code=303)


@app.get("/already_done", response_class=HTMLResponse)
def done_page(request: Request, session: SessionDep):
    tasks = session.exec(select(Task).where(Task.status == True)).all()
    return templates.TemplateResponse("marked_done.html", {"request": request, "tasks": tasks})


@app.post("/{task_id}")
def mark_as_done(task_id: int, session: SessionDep):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = True
    session.commit()

    return RedirectResponse(url="/", status_code=303)


@app.post("/already_done/{task_id}")
def delete_task(task_id: int, session: SessionDep):
    task = session.get(Task, task_id)
    if not task:
        return RedirectResponse('/')

    session.delete(task)
    session.commit()

    return RedirectResponse(url="/", status_code=303)


@app.get("/not_finished", response_class=HTMLResponse)
def not_done_yet(request: Request, session: SessionDep):
    tasks = session.exec(select(Task).where(Task.status == False)).all()

    return templates.TemplateResponse("not_finished.html", {"request": request, 'tasks': tasks})


if __name__ == "__main__":
    create_db_and_tables()
