import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib_fontja

load_dotenv()

# データ取得
connection_config = {
  'host': os.environ['DB_HOST'],
  'port': os.environ['DB_PORT'],
  'database': os.environ['DB_DATABASE'],
  'user': os.environ['DB_USER'],
  'password': os.environ['DB_PASSWORD']
}

connection = psycopg2.connect(**connection_config)
musicMaster = pd.read_sql(sql='SELECT * FROM "TbmMusic"', con=connection)
setlists = pd.read_sql(sql='SELECT * FROM "TbtSetlist"', con=connection)

# データ整形
musicMap = musicMaster \
  .sort_values(by='order')[['id', 'name', 'order']] \
  .set_index('id')
cell_col_names = ['cell_{}'.format(i) for i in range(1, 21)]

# 曲登場回数
def view_music_counts(setlists):
  music_id_counts = setlists \
    .melt(value_vars=cell_col_names, value_name='music_id')['music_id'] \
    .dropna() \
    .value_counts()
  
  music_id_counts_withM = pd.concat([musicMap, music_id_counts], axis=1)
  music_id_counts_withM = music_id_counts_withM.drop('_MC_')

  fig, ax = plt.subplots()
  ax.bar(music_id_counts_withM['name'], music_id_counts_withM['count'])
  plt.xticks(rotation=90)
  plt.tight_layout()
  plt.show()

view_music_counts(setlists)