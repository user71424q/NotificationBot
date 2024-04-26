import pandas as pd
import numpy as np
import datetime
import re
from pandas import DataFrame, Series
from io import BytesIO
def parse_excel(excel_file: bytes) -> DataFrame:
  return pd.read_excel(BytesIO(excel_file), usecols="A:D", names=['name', 'description', 'deadline', 'participants'])

def pandas_row_to_dict(data: Series) -> dict:
  """
  Получить 4 переменных, соответствующих четырем столбцам строки датафрейма
  :param_name data: строка датафрейма со столбцами 'name', 'description', 'deadline', 'participants'
  """
  name = str(data['name'] if data['name'] else "Безымянная задача")
  descr = str(data['description'])
  try:
    deadline = datetime.datetime.strptime(str(data['deadline']), '%Y-%m-%d %H:%M:%S')
  except ValueError:
    deadline = datetime.datetime.strptime(str(data['deadline']), '%Y-%m-%d %H:%M')
  particip = [item for item in re.split(r'[ ,@]+', data['participants'].strip()) if item]
  return {'name': name, 'description': descr, 'deadline': deadline, 'participants': particip}

def parse_pandas_dataframe(df_org: DataFrame) -> list[dict]:
  """
  Преобразовать датафрейм Pandas в словарь для последующей записи в БД
  :param_name df_org: Pandas датафрейм со столбцами 'name', 'description', 'deadline', 'participants'
  """
  res_list = []
  for i in range(0, len(df_org.index)):
    res_list.append(pandas_row_to_dict(df_org.iloc[i]))
  return res_list