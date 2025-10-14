from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse,  RedirectResponse
from typing import Annotated
from fastapi.templating import Jinja2Templates
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import Form
from fastapi import Depends, FastAPI, HTTPException, Request, Query
# create your app
app = FastAPI()
# inculde templates folder
templates = Jinja2Templates(directory="templates")


class Task(SQLModel, table=True):
    # create DB table
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    text: str | None = Field(default=None, index=True)
    status: bool = Field(index=True, default=False)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"


def create_db_and_tables():
    # create DB engine
    SQLModel.metadata.create_all(engine)


def get_session():

    # make working woth session safety
    with Session(engine) as session:
        yield session


connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SessionDep = Annotated[Session, Depends(get_session)]

create_db_and_tables()


@app.post("/main/{task_id}/done")
def mark_as_done(task_id: int, session: SessionDep):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = True
    session.commit()

    return RedirectResponse(url="/", status_code=303)


@app.get("/main", response_class=HTMLResponse)
def main_page(request: Request, session: SessionDep):
    tasks = session.exec(select(Task)).all()
    return templates.TemplateResponse(
        "main.html",
        {"request": request, "tasks": tasks}
    )


@app.get("/create", response_class=HTMLResponse)
# GET-method for create
def create_task(request: Request): return templates.TemplateResponse(
    "create_task.html", {'request': request})


@app.post("/create", response_class=HTMLResponse)
def create_page(request: Request, session: SessionDep, title: str = Form(...), text: str = Form(...), status: bool = Form(default=False)):
    task = Task(title=title, text=text, status=status)
    session.add(task)
    session.commit()
    session.refresh(task)
    return RedirectResponse(url="/main", status_code=303)


@app.get("/already_done", response_class=HTMLResponse)
def done_page(request: Request, session: SessionDep):
    tasks = session.exec(select(Task).where(Task.status == True)).all()
    return templates.TemplateResponse("marked_done.html", {"request": request, "tasks": tasks})


@app.post("/already_done/{{ task.id }}/delete", response_class=HTMLResponse)
def delete_task(request: Request, task_id: int, session: SessionDep):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()

    tasks = session.exec(select(Task).where(Task.status == True)).all()

    return templates.TemplateResponse(
        "marked_done.html",
        {"request": request, "tasks": tasks}
    )


@app.get("/not_finished", response_class=HTMLResponse)
def not_finished(request: Request):
    return templates.TemplateResponse("not_finished.html", {"request": request})
