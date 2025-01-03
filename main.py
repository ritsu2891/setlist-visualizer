import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
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
  .sort_values(by='order')[['id', 'name', 'short_name', 'order']] \
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

# 曲順グラフ
def view_music_order_graph(setlists):
  # 曲カラム名
  cell_col_names_withSE = ['cell_0'] + cell_col_names
  # カウント保持用のSeriesを作成
  musicToMusicCountSeries = pd.Series([], index=pd.MultiIndex.from_tuples([], names=['from', 'to']), name='count_sum')

  # 最初はSEで固定
  setlists = setlists.copy()
  setlists['cell_0'] = '_SE_'

  # 曲から曲へのカウントを集計
  for i in range(1, len(cell_col_names_withSE)):
    musicToMusicCountSeries_Work = setlists.value_counts([
      cell_col_names_withSE[i-1],
      cell_col_names_withSE[i]
    ])
    musicToMusicCountSeries_Work.index.names = ['from', 'to']

    musicToMusicCountSeries = pd.concat([musicToMusicCountSeries, musicToMusicCountSeries_Work], axis=1)
    musicToMusicCountSeries['count_sum'] = musicToMusicCountSeries.sum(axis=1)
    musicToMusicCountSeries = musicToMusicCountSeries.drop('count', axis=1)

  G = nx.MultiDiGraph()
  for cnt in musicToMusicCountSeries.reset_index().values.tolist():
    if (cnt[2] < 5):
      continue

    #if (cnt[0] == '_MC_' or cnt[1] == '_MC_') or (cnt[0] == '_SE_' or cnt[1] == '_SE_'):
      #continue

    G.add_edge(
      musicMap.loc[cnt[0]]['short_name'],
      musicMap.loc[cnt[1]]['short_name'],
      weight=cnt[2]
    )

  # 重みのリストを取得
  weights = nx.get_edge_attributes(G, 'weight').values()

  # カラーマップを作成
  norm = mcolors.Normalize(vmin=min(weights), vmax=max(weights))
  cmap = cm.get_cmap('Reds')

  # ポジションを計算
  pos = nx.nx_pydot.graphviz_layout(G)

  # ノードを描画
  nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=400)

  # エッジを描画（重みに応じて色を設定）
  for edge, weight in nx.get_edge_attributes(G, 'weight').items():
    color = cmap(norm(weight))  # 重みを色にマッピング
    nx.draw_networkx_edges(
      G, pos, edgelist=[edge], edge_color=[color], width=2,
      connectionstyle=f'arc3, rad = 0.25'
    )

  # ラベルを描画
  nx.draw_networkx_labels(G, pos, font_size=12, font_color='black', font_family='Osaka')
  nx.draw_networkx_edge_labels(
    G, pos,
    edge_labels=nx.get_edge_attributes(G, 'weight'),
    font_color='gray',
    connectionstyle=f'arc3, rad = 0.25'
  )

  # カラーバーを追加
  sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
  sm.set_array([])  # 必須
  plt.colorbar(sm, label='曲順回数', ax=plt.gca())

  # グラフを表示
  plt.title("曲順回数グラフ")
  plt.axis('off')
  plt.show()

#view_music_counts(setlists)
#view_music_order_graph(setlists)