import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import base64
import io
import os

# ページの設定
st.set_page_config(page_title="Unit Layout Viewer", layout="wide")
st.title("台レイアウト可視化")

# CSV読み込み（台番号は文字列として扱う）
csv_file = "unit_layout.csv"

if not os.path.exists(csv_file):
    st.error(f"エラー: '{csv_file}' が見つかりませんでした。実行中のフォルダにファイルがあるか確認してください。")
    st.stop()

df_layout = pd.read_csv(csv_file, dtype={'台番号': str})

# データが読み込めているか確認用
with st.expander("読み込んだデータを確認"):
    st.write(df_layout.head())

# サイドバーで「表示上の大きさ」を調整できるようにする
zoom_level = st.sidebar.slider("ズーム倍率 (1.0で画面幅にフィット)", min_value=0.5, max_value=8.0, value=1.0, step=0.1)

# Matplotlibを使ってSVGを作成する関数
def create_layout_svg(df):
    # 座標の範囲を取得
    min_x, max_x = df['座標X'].min(), df['座標X'].max()
    min_y, max_y = df['座標Y'].min(), df['座標Y'].max()
    
    # 図のサイズをデータ範囲に合わせて決定
    fig_w = (max_x - min_x) / 5
    fig_h = (max_y - min_y) / 5
    
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    
    # 1台のサイズ（CSVの座標間隔が5程度なので、3.5x3.5くらいが適切）
    u_w, u_h = 4.0, 4.0 
    
    for _, row in df.iterrows():
        # 四角形の描画
        rect = patches.Rectangle(
            (row['座標X'] - u_w/2, row['座標Y'] - u_h/2), 
            u_w, u_h, facecolor='RoyalBlue', edgecolor='white', linewidth=0.5
        )
        ax.add_patch(rect)
        
        # 台番号の描画（SVGなので、拡大時にこのテキストも一緒に大きくなる）
        ax.text(
            row['座標X'], row['座標Y'], row['台番号'],
            color='white', ha='center', va='center', fontsize=7, fontweight='bold'
        )

    ax.set_xlim(min_x - 10, max_x + 10)
    ax.set_ylim(max_y + 10, min_y - 10) # Y軸を反転（スプレッドシート形式）
    ax.set_aspect('equal')
    ax.axis('off') # グラフの枠や目盛りを消す
    
    buf = io.BytesIO()
    plt.savefig(buf, format='svg', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return buf.getvalue()

svg_bytes = create_layout_svg(df_layout)

# SVGバイト列をBase64文字列に変換してData URIを作成します。
# これにより、Pillowの画像形式判定を回避し、ブラウザ側でSVGをレンダリングさせます。
b64_svg = base64.b64encode(svg_bytes).decode("utf-8")
svg_url = f"data:image/svg+xml;base64,{b64_svg}"

# width を固定ピクセルではなく「%」にすることで、初期状態(1.0)でスマホ・PCそれぞれの画面幅に自動フィットさせます。
# ズームを上げると 100% を超えるため、スクロールが発生してPDFのような挙動になります。
st.markdown(
    f"""
    <div style="overflow: auto; max-height: 80vh; border: 1px solid #ddd; background-color: #f0f0f0;">
        <img src="{svg_url}" style="width: {int(zoom_level * 100)}%; max-width: none;">
    </div>
    """,
    unsafe_allow_html=True
)