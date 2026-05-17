import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import base64
import io
import os
import streamlit.components.v1 as components

# ページの設定
st.set_page_config(page_title="Unit Layout Viewer", layout="wide")
st.title("台レイアウト可視化")

# プロジェクト構造の定義（判断を容易にするため一箇所に集約）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# レイアウトファイルのアップロード（デフォルトはunit_layout.csv）
st.sidebar.markdown("### レイアウトファイル")
layout_file = st.sidebar.file_uploader(
    "レイアウトCSVをアップロード（任意）",
    type=None,
    help="レイアウトファイルを指定しない場合は、unit_layout.csvを使用します。"
)

# CSV読み込み（台番号は文字列として扱う）
if layout_file is not None:
    try:
        file_ext = os.path.splitext(layout_file.name)[1].lower()
        if file_ext not in ['.csv', '.txt']:
            st.error(f"エラー: CSVまたはテキストファイルをアップロードしてください (選択されたファイル: {layout_file.name})")
            st.stop()

        layout_file.seek(0)
        try:
            df_layout = pd.read_csv(layout_file, dtype={'台番号': str})
        except UnicodeDecodeError:
            layout_file.seek(0)
            df_layout = pd.read_csv(layout_file, dtype={'台番号': str}, encoding='cp932')
    except Exception as e:
        st.error(f"レイアウトファイルの読み込み中にエラーが発生しました: {e}")
        st.stop()
else:
    csv_file = os.path.join(BASE_DIR, "unit_layout.csv")
    if not os.path.exists(csv_file):
        st.error(f"エラー: '{csv_file}' が見つかりませんでした。実行中のフォルダにファイルがあるか確認してください。")
        st.stop()
    df_layout = pd.read_csv(csv_file, dtype={'台番号': str})

df_layout['台番号'] = df_layout['台番号'].str.strip() # 前後の空白を削除
# 数値として比較するために数値変換した列を用意（表示用には元の文字列を使用）
df_layout['台番号_numeric'] = pd.to_numeric(df_layout['台番号'], errors='coerce')

# 台番号の重複チェック（数値として同一視されるものを含む）
duplicate_mask = df_layout.duplicated('台番号_numeric', keep=False) & df_layout['台番号_numeric'].notna()
if duplicate_mask.any():
    duplicate_list = sorted(df_layout.loc[duplicate_mask, '台番号'].unique())
    layout_source = layout_file.name if layout_file is not None else "unit_layout.csv"
    st.warning(f"注意: レイアウトデータ ({layout_source}) 内で台番号が重複しています: {duplicate_list}")

# ハイライト対象のCSV読み込み
st.sidebar.markdown("---")
st.sidebar.markdown("### テストデータ")
uploaded_file = st.sidebar.file_uploader(
    "CSVデータをアップロード",
    type=None,  # 制限を外してOSのファイルピッカーに全てのファイルを表示させる
    help="**【スマホでドライブ上のファイルを選びたい場合】**\n\nファイル選択画面で『ドライブ』や『ファイル』アプリを選択してください。\nもし選択しても反応がない場合は、一度端末に『ダウンロード』してから選択してください。"
)

test_units = set()
if uploaded_file is not None:
    try:
        # ファイル形式の簡易チェック
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in ['.csv', '.txt']:
            st.error(f"エラー: CSVまたはテキストファイルをアップロードしてください (選択されたファイル: {uploaded_file.name})")
            st.stop()

        # 日本語環境(Excel)で保存されたCSVでも読み込めるようエンコーディングを自動調整
        uploaded_file.seek(0)
        try:
            df_test_all = pd.read_csv(uploaded_file, dtype={'台番号': str})
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df_test_all = pd.read_csv(uploaded_file, dtype={'台番号': str}, encoding='cp932')
        
        df_test_all['台番号'] = df_test_all['台番号'].str.strip()

        # 必須カラムの存在チェック
        if '日付' not in df_test_all.columns:
            st.error("アップロードされたCSVに『日付』列が見つかりません。")
        else:
            # 日付の選択肢を取得（降順で最新を上に）
            available_dates = sorted(df_test_all['日付'].unique(), reverse=True)
            selected_date = st.sidebar.selectbox("表示対象日の選択", available_dates)

            # 選択された日付のデータのみを抽出
            df_test = df_test_all[df_test_all['日付'] == selected_date]
            total_test_rows = len(df_test)
            event_name = df_test['イベント名'].iloc[0] if 'イベント名' in df_test.columns else "不明なイベント"

            # 比較対象も数値に変換してセットに格納
            test_units = set(pd.to_numeric(df_test['台番号'], errors='coerce').dropna().unique())
            
            # レイアウト側に存在する台番号のセットを作成し、差分（一致しなかった台）を抽出
            layout_units_set = set(df_layout['台番号_numeric'].dropna().unique())
            unmatched_units = test_units - layout_units_set

            matched_count = int(df_layout['台番号_numeric'].isin(test_units).sum())
            st.subheader(f"対象日: {selected_date} ({event_name})")

            # データの整合性チェック
            is_all_ok = (total_test_rows == len(test_units) == matched_count)

            if is_all_ok:
                st.success(f"✅ 全 {matched_count} 台のデータが正常に一致しました。")
            else:
                st.error("⚠️ データに不一致があります。内容を確認してください。")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("CSVデータ総数", f"{total_test_rows} 件")
                with col2:
                    invalid_diff = len(test_units) - total_test_rows
                    st.metric("有効な台数", f"{len(test_units)} 台", 
                              delta=f"{invalid_diff} (重複/無効)" if invalid_diff != 0 else None, delta_color="inverse")
                with col3:
                    missing_diff = matched_count - len(test_units)
                    st.metric("レイアウト一致", f"{matched_count} 台", 
                              delta=f"{missing_diff} (未配置)" if missing_diff != 0 else None, delta_color="inverse")

            if unmatched_units:
                # 表示用に数値をソートし、整数は整数の形式でリスト化
                unmatched_list = sorted([int(x) if x == int(x) else x for x in unmatched_units])
                st.warning(f"レイアウト内に見つからなかった台番号 ({len(unmatched_units)}台): {unmatched_list}")
    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
else:
    st.info("サイドバーから CSV ファイルをアップロードしてください。現在は通常色で描画しています。")

# データが読み込めているか確認用
with st.expander("読み込んだデータを確認"):
    st.write(df_layout.head())

# Matplotlibを使ってSVGを作成する関数
def create_layout_svg(df, highlight_units):
    # 座標の範囲を取得
    min_x, max_x = df['座標X'].min(), df['座標X'].max()
    min_y, max_y = df['座標Y'].min(), df['座標Y'].max()
    
    # 図のサイズをデータ範囲に合わせて決定
    fig_w = (max_x - min_x) / 5
    fig_h = (max_y - min_y) / 5
    
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    
    # 1台のサイズ（CSVの座標間隔が5程度なので、3.5x3.5くらいが適切）
    u_w, u_h = 5.0, 5.0 
    
    for _, row in df.iterrows():
        # 台番号がテスト用リストに含まれているかチェック
        is_highlight = row['台番号_numeric'] in highlight_units
        box_color = 'OrangeRed' if is_highlight else 'RoyalBlue'

        # 四角形の描画
        rect = patches.Rectangle(
            (row['座標X'] - u_w/2, row['座標Y'] - u_h/2), 
            u_w, u_h, facecolor=box_color, edgecolor='white', linewidth=0.5
        )
        ax.add_patch(rect)
        
        # 台番号の描画（SVGなので、拡大時にこのテキストも一緒に大きくなる）
        ax.text(
            row['座標X'], row['座標Y'], row['台番号'],
            color='white', ha='center', va='center', fontsize=16, fontweight='bold'
        )

    ax.set_xlim(min_x - 10, max_x + 10)
    ax.set_ylim(max_y + 10, min_y - 10) # Y軸を反転（スプレッドシート形式）
    ax.set_aspect('equal')
    ax.axis('off') # グラフの枠や目盛りを消す
    
    buf = io.BytesIO()
    plt.savefig(buf, format='svg', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return buf.getvalue()

svg_bytes = create_layout_svg(df_layout, test_units)

# SVGバイト列をBase64文字列に変換してData URIを作成します。
# これにより、Pillowの画像形式判定を回避し、ブラウザ側でSVGをレンダリングさせます。
b64_svg = base64.b64encode(svg_bytes).decode("utf-8")
svg_url = f"data:image/svg+xml;base64,{b64_svg}"

# width を固定ピクセルではなく「%」にすることで、初期状態(1.0)でスマホ・PCそれぞれの画面幅に自動フィットさせます。
# ズームを上げると 100% を超えるため、スクロールが発生してPDFのような挙動になります。
# マウスホイールでのズーム機能を追加（マウス位置基準）
components.html(
    f"""
    <div style="overflow: auto; max-height: 80vh; border: 1px solid #ddd; background-color: #f0f0f0;" id="svg-container">
        <img src="{svg_url}" id="svg-image" style="width: 100%; max-width: none; transition: width 0.1s ease-out;">
    </div>
    <div style="margin-top: 10px;">
        <button id="reset-zoom" style="padding: 8px 16px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
            ズームをリセット (1.0倍)
        </button>
    </div>
    <script>
        const container = document.getElementById('svg-container');
        const image = document.getElementById('svg-image');
        const resetButton = document.getElementById('reset-zoom');
        let currentZoom = 1.0;
        
        // マウスホイールでのズーム（マウス位置基準）
        container.addEventListener('wheel', function(e) {{
            e.preventDefault();
            
            // マウスのコンテナ内での相対位置を取得
            const rect = container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            // 現在のスクロール位置
            const scrollLeft = container.scrollLeft;
            const scrollTop = container.scrollTop;
            
            // ズーム前の画像幅
            const oldWidth = image.offsetWidth;
            
            // ホイールの方向に応じてズーム
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            const newZoom = Math.max(0.5, Math.min(8.0, currentZoom + delta));
            
            // ズーム後の画像幅
            image.style.width = (newZoom * 100) + '%';
            const newWidth = image.offsetWidth;
            
            // マウス位置を基準にスクロール位置を調整
            const widthRatio = newWidth / oldWidth;
            container.scrollLeft = (scrollLeft + mouseX) * widthRatio - mouseX;
            container.scrollTop = (scrollTop + mouseY) * widthRatio - mouseY;
            
            currentZoom = newZoom;
        }}, {{ passive: false }});
        
        // リセットボタン
        resetButton.addEventListener('click', function() {{
            currentZoom = 1.0;
            image.style.width = '100%';
            container.scrollLeft = 0;
            container.scrollTop = 0;
        }});
    </script>
    """,
    height=650
)