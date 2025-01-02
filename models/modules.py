from enum import Enum
from typing import List

import pandas as pd
from pydantic import Field

from models.basemodel import BaseModel
from helpers.openai_wrapper import call_openai
from helpers.text_utils import read_prompt, slugify, snake_to_title
from helpers.readers import read_docx, read_excel, read_mp3, read_pdf, read_wav


class TaskCategory(str, Enum):
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    AI = "AI"

    @classmethod
    def comma_separated(cls):
        return ", ".join(x.value for x in TaskCategory)


class TaskCategoryModel(BaseModel):
    category: TaskCategory = f"Can be one of {TaskCategory.comma_separated()}"
    hours: float = Field(
        "Estimated amount of hours required. Must be an int or float", gt=0
    )
    subtask: str = "Short description of the task"


class TaskModel(BaseModel):
    task: str = "Name of the task"
    description: str = "Description of the Task along with what to implement"
    categories: List[TaskCategoryModel] = [
        TaskCategoryModel(category=c.value) for c in TaskCategory
    ]


class ModuleModel(BaseModel):
    module: str = "Name of the bigger module which the tasks are a part of."
    tasks: List[TaskModel] = [TaskModel()]


class Modules(BaseModel):
    project_name: str = "Name of the project."
    modules: List[ModuleModel] = [ModuleModel()]

    @property
    def slug(self):
        return slugify(self.project_name)

    @classmethod
    def from_sow(cls, sow: str):
        prompt = read_prompt(
            "user",
            {
                "sow": sow,
                "categories": TaskCategory.comma_separated(),
                "output_format": Modules().to_yaml(),
            },
        )
        resp = call_openai(messages=[{"role": "user", "content": prompt}], model="gpt-4o")
        return cls.from_yaml(resp)

    @classmethod
    def from_pdf(cls, pdf_path: str):
        return cls.from_sow(read_pdf(pdf_path))

    @classmethod
    def from_docx(cls, docx_path: str):
        return cls.from_sow(read_docx(docx_path))
    
    @classmethod
    def from_excel(cls, excel_path: str):
        return cls.from_sow(read_excel(excel_path))

    @classmethod
    def from_mp3(cls, mp3_path: str):
        return cls.from_sow(read_mp3(mp3_path))
    
    @classmethod
    def from_wav(cls, wav_path: str):
        return cls.from_sow(read_wav(wav_path))

    @staticmethod
    def pivot_df_by_categories(df: pd.DataFrame):
        pivot1 = df.pivot_table(
            index=["module", "task", "description"],
            columns="category",
            values=["hours"],
            aggfunc="sum",
            fill_value=0,
        )
        pivot2 = df.pivot_table(
            index=["module", "task", "description"],
            columns="category",
            values=["subtask"],
            aggfunc=lambda x: ", ".join(x),
            fill_value="",
        )
        pivot = pivot1.merge(pivot2, left_index=True, right_index=True)

        # Flatten the multi-index columns
        pivot.columns = [f"{col[1]}_{col[0]}" for col in pivot.columns]
        # Sort the columns
        pivot = pivot.reindex(columns=sorted(pivot.columns))
        # Reset index to make it a proper DataFrame
        pivot = pivot.reset_index()

        return pivot

    def to_df(self, title_cased: bool = False, pivot_by_categories: bool = False):
        df = pd.DataFrame(
            [
                {
                    "module": module.module,
                    **task.to_dict(exclude=["categories"]),
                    **category.to_dict(),
                }
                for module in self.modules
                for task in module.tasks
                for category in task.categories
            ]
        )
        if pivot_by_categories:
            df = self.pivot_df_by_categories(df)
        if title_cased:
            df.columns = map(snake_to_title, df.columns)
        return df

    def __hash__(self):
        return hash(self.to_yaml())
