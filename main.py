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
setlists['date_cv'] = pd.to_datetime(setlists['date'], format='%Y/%m/%d')

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

# 曲登場回数（表）
def view_music_counts_table(setlists, yearMonth=None):
  setlists_t = setlists.copy()
  if yearMonth is not None:
    setlists_t = setlists[setlists['date_cv'].dt.strftime('%Y/%m') == yearMonth]

  music_id_counts = setlists_t \
    .melt(value_vars=cell_col_names, value_name='music_id')['music_id'] \
    .dropna() \
    .value_counts()
  
  music_id_counts_withM = pd.concat([musicMap, music_id_counts], axis=1)
  music_id_counts_withM = music_id_counts_withM.drop('_MC_')

  music_id_counts_display = music_id_counts_withM[['name', 'count']].sort_values(by='count', ascending=False)

  music_id_counts_display['percent'] = music_id_counts_display['count'] / setlists['artist_id'].count() * 100
  music_id_counts_display.set_index('name', inplace=True)
  music_id_counts_display.index.names = ['曲名']
  music_id_counts_display.columns = ['回数', '割合(%)']
  music_id_counts_display

# 曲登場回数（グラフ）
def view_music_counts_graph(setlists, yearMonth=None):
  setlists_t = setlists.copy()
  if yearMonth is not None:
    setlists_t = setlists[setlists['date_cv'].dt.strftime('%Y/%m') == yearMonth]

  music_id_counts = setlists_t \
    .melt(value_vars=cell_col_names, value_name='music_id')['music_id'] \
    .dropna() \
    .value_counts()
  
  music_id_counts_withM = pd.concat([musicMap, music_id_counts], axis=1)
  music_id_counts_withM = music_id_counts_withM.drop('_MC_')

  fig, ax = plt.subplots()
  p = ax.bar(music_id_counts_withM['name'], music_id_counts_withM['count'])
  #ax.bar_label(p, label_type='edge')

  values = music_id_counts_withM['count']
  percentages = music_id_counts_withM['count'] / setlists['artist_id'].count() * 100
  for i, (value, percentage) in enumerate(zip(values, percentages)):
    plt.text(i, value + 1, f"{value:.0f}\n({percentage:.1f}%)", ha='center', fontsize=8)

  plt.ylim(0, music_id_counts_withM['count'].max() * 1.2)
  plt.xticks(rotation=90)
  plt.xlabel('曲名')
  plt.ylabel('回数')
  if yearMonth is not None:
    plt.title(yearMonth + ' 曲採用頻度')
  else:
    plt.title('曲採用頻度')
  plt.tight_layout()
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
  musicToMusicCountSeries_pivot.index.name = '曲名'
  
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
  plt.title('曲順ヒートマップ')
  plt.colorbar(heatmap)
  plt.tight_layout()
  st.pyplot(plt)

# 曲順グラフ
def view_music_order_graph(setlists, withSEMC):
  fig, ax = plt.subplots()
  plt.figure(figsize=(12, 8))

  musicToMusicCountSeries = gen_musicToMusic_data(setlists)
  musicToMusicCountArr = musicToMusicCountSeries \
    .reset_index().values.tolist()

  G = nx.MultiDiGraph()
  for cnt in musicToMusicCountArr:
    if (withSEMC and cnt[2] < 5):
      continue
    if (not withSEMC and cnt[2] < 3):
      continue

    if not withSEMC and ((cnt[0] == '_MC_' or cnt[1] == '_MC_') or (cnt[0] == '_SE_' or cnt[1] == '_SE_')):
      continue

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
  pos = nx.circular_layout(G)

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
  nx.draw_networkx_labels(G, pos, font_size=12, font_color='black', font_family='IPAexGothic')

  edge_labels = {edge: int(attr) for edge, attr in nx.get_edge_attributes(G, 'weight').items()}
  
  nx.draw_networkx_edge_labels(
    G, pos,
    edge_labels=edge_labels,
    font_color='gray',
    connectionstyle=f'arc3, rad = 0.25'
  )

  # カラーバーを追加
  sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
  sm.set_array([])  # 必須
  plt.colorbar(sm, label='曲順回数', ax=plt.gca())

  # グラフを表示
  if withSEMC:
    plt.title("曲順回数グラフ（SE/MCあり）")
  else:
    plt.title("曲順回数グラフ（SE/MCなし）")
  plt.axis('off')
  
  st.pyplot(plt)
  if withSEMC:
    '※5回以上のみ表示しています'
  else:
    '※3回以上のみ表示しています'

'# アスうさセトリ'
'このページは **[アストリーのうさぎ](https://x.com/Asutory_Usagi)** のセトリから、曲の採用頻度や曲順などを可視化した結果を表示します。セトリ情報はメンバーの **[桐いろは](https://x.com/AsuUsa_kiri)** さんのXポストを収集・パースして作成したデータを使用しています。（収集期間：' + setlists['date'].min().strftime('%Y/%m/%d') + '〜' + setlists['date'].max().strftime('%Y/%m/%d') + '）'

'## 曲採用頻度'
'全て'
view_music_counts_table(setlists)
'2024/12'
view_music_counts_table(setlists, '2024/12')
'2024/11'
view_music_counts_table(setlists, '2024/11')
'2024/10'
view_music_counts_table(setlists, '2024/10')

view_music_counts_graph(setlists)
view_music_counts_graph(setlists, '2024/12')
view_music_counts_graph(setlists, '2024/11')
view_music_counts_graph(setlists, '2024/10')

'## 曲順'
view_music_order_heatmap(setlists)
view_music_order_graph(setlists, True)
view_music_order_graph(setlists, False)

'## 再配布'
'このページに掲載しているデータ・画像等は、 **このページからの引用であることを明記の上で**再配布可能とします。'

'## お問い合わせ'
'このページに関するお問い合わせは [rpakaのXアカウント](https://x.com/ritsu2891) にDMでお願いします。'

'---'
'v1.0.2 (2025-01-24)　[GitHub](https://github.com/ritsu2891/setlist-visualizer)'
#expand = st.expander("My label", icon=":material/info:", expanded=True)
#expand.write("Inside the expander.")