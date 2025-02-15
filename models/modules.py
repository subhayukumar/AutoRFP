import csv
import json
from enum import Enum
from typing import List

import pandas as pd
from pydantic import Field
import plotly.graph_objects as go

from helpers.utils import hash_uuid
from models.basemodel import BaseModel
from config import SANKEY_TEMPLATE_PATH
from helpers.openai_wrapper import call_openai
from helpers.text_utils import read_prompt, slugify, snake_to_title
from helpers.readers import (
    read_docx,
    read_excel,
    read_mp3,
    read_pdf,
    read_wav,
    read_text,
)


class TaskCategory(str, Enum):
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    AI = "AI"

    @classmethod
    def comma_separated(cls):
        return ", ".join(x.value for x in TaskCategory)


class TaskCategoryModel(BaseModel):
    category: TaskCategory | str = f"Can be one of {TaskCategory.comma_separated()}"
    hours: float = Field(
        "Estimated amount of hours required. Must be an int or float greater than 0", ge=0
    )
    subtask: str = "Short description of the task"
    short_name: str = "A very short name for the subtask (2-4 words). Must be unique."


class TaskModel(BaseModel):
    task: str = "Name of the task"
    description: str = "Description of the Task along with what to implement"
    categories: List[TaskCategoryModel] = [
        TaskCategoryModel(category=c.value) for c in TaskCategory
    ]
    short_name: str = "A very short name for the task (2-4 words). Must be unique."

    @property
    def hours(self):
        return sum([c.hours for c in self.categories])
    
    @property
    def subtasks(self):
        return len(self.categories)


class ModuleModel(BaseModel):
    module: str = "Name of the bigger module which the tasks are a part of."
    short_name: str = "A very short name for the module (2-4 words). Must be unique."
    tasks: List[TaskModel] = [TaskModel()]
    
    @property
    def hours(self):
        return sum([t.hours for t in self.tasks])
    
    @property
    def subtasks(self):
        return sum([t.subtasks for t in self.tasks])


class Modules(BaseModel):
    project_name: str = "Name of the project."
    modules: List[ModuleModel] = [ModuleModel()]

    @property
    def slug(self):
        return slugify(self.project_name)
    
    @property
    def hours(self):
        return sum([m.hours for m in self.modules])
    
    @property
    def subtasks(self):
        return sum([m.subtasks for m in self.modules])

    @classmethod
    def from_sow(cls, sow: str, best_of: int = 3, regenerate: bool = False):
        """
        Creates a Modules object from a Statement of Work (SOW) string.

        Args:
            sow (str): The SOW string.
            best_of (int): The number of best responses to consider. Defaults to 3.
            regenerate (bool): If True, the object will be regenerated even if it already exists in the cache. Defaults to False.

        Returns:
            Modules: The Modules object created from the SOW string.
        """
        sow_hash = hash_uuid(sow).hex
        
        # Try to load the object from the cache
        if not regenerate:
            obj = cls.load_from_cache(key=sow_hash, return_as_dict=False)
            if obj and isinstance(obj, cls):
                return obj
        
        # Generate the prompt for the AI
        prompt = read_prompt(
            "user",
            {
                "sow": sow,
                "categories": TaskCategory.comma_separated(),
                "output_format": Modules().to_yaml(),
            },
        )
        
        # Ask the AI to generate responses
        responses = call_openai(
            messages=[{"role": "user", "content": prompt}], 
            model="gpt-4o", 
            temperature=0.2, 
            n=best_of, 
        )
        
        # Parse the responses and create Modules objects
        objects = sorted(
            [cls.from_yaml(resp) for resp in responses], 
            key=lambda x: (x.subtasks, x.hours), 
            reverse=True, 
        )
        
        # Take the best response and save it to the cache
        obj = objects[0]
        obj.save_to_cache(key=sow_hash, background=True)
        
        return obj
    
    @classmethod
    def from_file(cls, path: str, best_of: int = 3, regenerate: bool = False):
        """
        Creates a Modules object from a file.

        This method supports various file formats, including PDF, DOCX, XLSX, MP3, WAV, YAML, and JSON.
        It reads the content of the file, processes it, and returns a Modules object based on the file's data.

        Args:
            path (str): The path to the file to be processed.
            best_of (int, optional): The number of best responses to consider when generating
                the Modules object. Defaults to 3.
            regenerate (bool, optional): If True, the object will be regenerated even if it
                already exists in the cache. Defaults to False.

        Returns:
            Modules: The Modules object created from the file data.

        Raises:
            ValueError: If the file format is unsupported.
        """
        ext = path.split(".")[-1]
        if ext == "pdf":
            data = read_pdf(path)
        elif ext == "docx":
            data = read_docx(path)
        elif ext == "xlsx":
            data = read_excel(path)
        elif ext == "mp3":
            data = read_mp3(path)
        elif ext == "wav":
            data = read_wav(path)
        elif ext in ["txt", "md"]:
            data = read_text(path)
        elif ext in ["yml", "yaml", "json"]:
            return super().from_file(path)
        else:
            raise ValueError("Unsupported file format!")
        return cls.from_sow(data, best_of, regenerate)

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
    
    @staticmethod
    def to_csv(df: pd.DataFrame, add_total_hours_row: bool = True) -> str:
        df = df.copy()
        if add_total_hours_row:
            df.loc[len(df)] = [x if isinstance(x, (float, int)) else "" for x in df.sum()]
        csv_text = df.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC)
        return csv_text

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
    
    def to_plotly_fig(self):
        df = pd.DataFrame([
            {
                "project": self.project_name,
                "module": module.short_name,
                "task": task.short_name,
                # "category": str(category.category),
                "subtask": category.short_name,
                "hours": category.hours,
            }
            for module in self.modules
            for task in module.tasks
            for category in task.categories
        ])


        dims = [
            go.parcats.Dimension(values=df[x], label=x.title())
            for x in df.columns
            if df[x].dtype == pd.StringDtype
        ]

        fig = go.Figure(
            go.Parcats(
                dimensions=dims,
                counts=df["hours"],
                line=go.parcats.Line(
                    color=df["module"].astype("category").cat.codes,
                    shape="hspline",
                ),
                hoveron="color",
                hoverinfo="count",
                labelfont=go.parcats.Labelfont(size=13),
                tickfont=go.parcats.Tickfont(),
                arrangement="freeform",
            )
        )
        return fig
    
    def to_sankey_html(self):
        if not SANKEY_TEMPLATE_PATH.exists():
            return ""
        
        df = pd.DataFrame([
            {
                "project": "P."+self.project_name,
                "module": "M."+module.short_name,
                "task": "T."+task.short_name,
                "subtask": "ST."+category.short_name,
                "hours": category.hours,
            }
            for module in self.modules
            for task in module.tasks
            for category in task.categories
        ])
        pm_df = (
            df.groupby(["project", "module"])
            .agg({"hours": "sum"})
            .reset_index()
            .rename(columns={"project": "from", "module": "to", "hours": "value"})
        )
        mt_df = (
            df.groupby(["module", "task"])
            .agg({"hours": "sum"})
            .reset_index()
            .rename(columns={"module": "from", "task": "to", "hours": "value"})
        )
        ts_df = (
            df.groupby(["task", "subtask"])
            .agg({"hours": "sum"})
            .reset_index()
            .rename(columns={"task": "from", "subtask": "to", "hours": "value"})
        )

        three_col_df = pd.concat([
            pm_df,
            mt_df,
            ts_df,
        ])
        sankey_data = three_col_df.to_dict(orient="records")
        html = SANKEY_TEMPLATE_PATH.read_text(encoding="utf-8")
        html = html.replace("{{SANKEY_JSON}}", json.dumps(sankey_data))
        return html

    def __hash__(self):
        return hash(self.to_yaml())
