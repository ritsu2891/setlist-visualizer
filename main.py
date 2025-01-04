import os
from dotenv import load_dotenv
import psycopg2
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib_fontja
import streamlit as st

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

# 曲順データ生成
def gen_musicToMusic_data(setlists):
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

  return musicToMusicCountSeries

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

  music_id_counts_display = music_id_counts_withM[['name', 'count']].sort_values(by='count', ascending=False)

  music_id_counts_display['percent'] = music_id_counts_display['count'] / setlists['artist_id'].count() * 100
  music_id_counts_display

  fig, ax = plt.subplots()
  ax.bar(music_id_counts_withM['name'], music_id_counts_withM['count'])
  plt.xticks(rotation=90)
  plt.tight_layout()
  st.pyplot(plt)

# 曲順グラフ
def view_music_order_graph(setlists):
  fig, ax = plt.subplots()
  plt.figure(figsize=(12, 8))

  musicToMusicCountSeries = gen_musicToMusic_data(setlists)
  musicToMusicCountArr = musicToMusicCountSeries \
    .reset_index().values.tolist()

  G = nx.MultiDiGraph()
  for cnt in musicToMusicCountArr:
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
  
  st.pyplot(plt)

# 曲順ヒートマップ
def view_music_order_heatmap(setlists):
  from_musicMap = musicMap.copy()
  from_musicMap = from_musicMap.add_prefix('from_')
  to_musicMap = musicMap.copy()
  to_musicMap = to_musicMap.add_prefix('to_')

  musicToMusicCountSeries = gen_musicToMusic_data(setlists)
  musicToMusicCountSeries = musicToMusicCountSeries.reset_index()
  musicToMusicCountSeries = pd.merge(musicToMusicCountSeries, from_musicMap, how='inner', left_on='from', right_on='id')
  musicToMusicCountSeries = pd.merge(musicToMusicCountSeries, to_musicMap, how='inner', left_on='to', right_on='id')

  musicToMusicCountSeries_pivot = musicToMusicCountSeries.pivot(index='from_short_name', columns='to_short_name', values='count_sum')
  musicToMusicCountSeries_pivot = musicToMusicCountSeries_pivot.reindex(index=musicMap['short_name'], columns=musicMap['short_name'])
  musicToMusicCountSeries_pivot = musicToMusicCountSeries_pivot.fillna(0)
  
  '縦：from　横：to'
  musicToMusicCountSeries_pivot

  fig, ax = plt.subplots()
  heatmap = ax.pcolor(musicToMusicCountSeries_pivot, cmap=plt.cm.Reds)
  ax.invert_yaxis()
  ax.xaxis.tick_top()
  plt.xticks(ticks=np.arange(len(musicToMusicCountSeries_pivot.columns))+0.5, labels=musicToMusicCountSeries_pivot.columns, rotation=90)
  plt.yticks(ticks=np.arange(len(musicToMusicCountSeries_pivot.index))+0.5, labels=musicToMusicCountSeries_pivot.index)
  plt.xlabel('To')
  plt.ylabel('From')
  plt.colorbar(heatmap)
  plt.tight_layout()
  st.pyplot(plt)

'# アスうさセトリ'
'このページは **[アストリーのうさぎ](https://x.com/Asutory_Usagi)** のセトリから、曲の採用頻度や曲順などを可視化した結果を表示します。セトリ情報はメンバーの **[桐いろは](https://x.com/AsuUsa_kiri)** さんのXポストを収集・パースして作成したデータを使用しています。（収集期間：' + setlists['date'].min().strftime('%Y/%m/%d') + '〜' + setlists['date'].max().strftime('%Y/%m/%d') + '）'

'## 曲採用頻度'
view_music_counts(setlists)

'## 曲順'
view_music_order_heatmap(setlists)
view_music_order_graph(setlists)

'## 再配布'
'このページに掲載しているデータ・画像等は、 **このページからの引用であることを明記の上で**再配布可能とします。'

'## お問い合わせ'
'このページに関するお問い合わせは [rpakaのXアカウント](https://x.com/ritsu2891) にDMでお願いします。'
#expand = st.expander("My label", icon=":material/info:", expanded=True)
#expand.write("Inside the expander.")