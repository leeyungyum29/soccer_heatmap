import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform
import os
import io
import re
import urllib.request
from matplotlib.colors import LinearSegmentedColormap

# =========================================================
# 1. Streamlit Cloud 전용 나눔고딕 폰트 자동 다운로드 및 등록
# =========================================================
@st.cache_resource
def setup_korean_font():
    sys_name = platform.system()
    if sys_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif sys_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        font_path = "NanumGothic.ttf"
        if not os.path.exists(font_path):
            url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
            urllib.request.urlretrieve(url, font_path)
        
        fm.fontManager.addfont(font_path)
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rc('font', family=font_name)

setup_korean_font()
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="축구 팀별 맞춤 히트맵 분석기", layout="wide")

# 파일명에서 경기 번호, 날짜, 팀명 자동 파싱 함수 (언더바 _ 및 공백 분할 대응)
def parse_match_metadata(home_files, away_files):
    match_no = "01"
    match_date = "0810"
    home_team = "홈팀"
    away_team = "어웨이팀"

    all_files = (home_files or []) + (away_files or [])
    for f in all_files:
        filename = os.path.splitext(f.name)[0].strip()
        
        # '0811_01' 또는 '01_0810' 파싱
        m1 = re.search(r'(\d{4})_(\d{2})', filename)
        if m1:
            match_date = m1.group(1)
            match_no = m1.group(2)
            break
            
        m2 = re.search(r'(\d{2})_(\d{4})', filename)
        if m2:
            match_no = m2.group(1)
            match_date = m2.group(2)
            break

    # 팀명 추출 (언더바 _ 나 띄어쓰기로 분할 후 맨 마지막 단어)
    if home_files:
        filename = os.path.splitext(home_files[0].name)[0].strip()
        tokens = re.split(r'[_ ]+', filename)
        if tokens:
            home_team = tokens[-1]

    if away_files:
        filename = os.path.splitext(away_files[0].name)[0].strip()
        tokens = re.split(r'[_ ]+', filename)
        if tokens:
            away_team = tokens[-1]

    return match_no, match_date, home_team, away_team

# 파일 로드 도우미
def load_multiple_files(files):
    if not files:
        return None
    df_list = []
    for file in files:
        if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
            temp_df = pd.read_excel(file)
        else:
            temp_df = pd.read_csv(file)
        
        if '경기시점' not in temp_df.columns:
            if '전반' in file.name:
                temp_df['경기시점'] = '전반'
            elif '후반' in file.name:
                temp_df['경기시점'] = '후반'
        df_list.append(temp_df)
    
    return pd.concat(df_list, ignore_index=True) if df_list else None

# '공격 루트 시작' ~ '공격 루트 종료' 구간 시퀀스 추출
def extract_route_sequence(df):
    col_opts = df.columns.tolist()
    col_event = next((c for c in ['이벤트명', '이벤트', 'event', 'Event'] if c in col_opts), None)
    
    if col_event is None:
        return df

    in_sequence = False
    valid_indices = []
    
    for idx, row in df.iterrows():
        event_val = str(row[col_event]).strip()
        
        if '공격' in event_val and '시작' in event_val:
            in_sequence = True
            valid_indices.append(idx)
        elif '공격' in event_val and ('종료' in event_val or '끝' in event_val):
            if in_sequence:
                valid_indices.append(idx)
            in_sequence = False
        else:
            if in_sequence:
                valid_indices.append(idx)
                
    return df.loc[valid_indices].copy()

# =========================================================
# 2. 맞춤 축구장 피치(105m x 68m 기본값) 및 화살표 그리기
# =========================================================
def draw_pitch_lines(ax, pitch_x=105.0, pitch_y=68.0, line_color='#C5C8CE', attack_dir="L->R"):
    ax.plot([0, 0, pitch_x, pitch_x, 0], [0, pitch_y, pitch_y, 0, 0], color=line_color, lw=2.5)
    ax.plot([pitch_x/2, pitch_x/2], [0, pitch_y], color=line_color, lw=2.5)
    
    center_circle = plt.Circle((pitch_x/2, pitch_y/2), 9.15, color=line_color, fill=False, lw=2.5)
    ax.add_patch(center_circle)
    ax.plot(pitch_x/2, pitch_y/2, 'o', color=line_color, ms=4)
    
    box_y_bottom = (pitch_y - 40.32) / 2
    box_y_top = (pitch_y + 40.32) / 2
    goal_y_bottom = (pitch_y - 18.32) / 2
    goal_y_top = (pitch_y + 18.32) / 2
    
    ax.plot([0, 16.5, 16.5, 0], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2.5)
    ax.plot([0, 5.5, 5.5, 0], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2.5)
    
    ax.plot([pitch_x, pitch_x - 16.5, pitch_x - 16.5, pitch_x], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2.5)
    ax.plot([pitch_x, pitch_x - 5.5, pitch_x - 5.5, pitch_x], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2.5)
    
    ax.plot([0, -2, -2, 0], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color='#A0A4AB', lw=2.5)
    ax.plot([pitch_x, pitch_x + 2, pitch_x + 2, pitch_x], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color='#A0A4AB', lw=2.5)

    arrow_y = -3.5
    if attack_dir == "L->R":
        ax.annotate(
            '공격 방향 (Attack) ▶', 
            xy=(pitch_x * 0.7, arrow_y), 
            xytext=(pitch_x * 0.3, arrow_y),
            arrowprops=dict(facecolor='#71757E', edgecolor='#71757E', width=2, headwidth=8, headlength=10),
            ha='center', va='center', color='#555962', fontsize=12, fontweight='bold'
        )
    else:
        ax.annotate(
            '◀ 공격 방향 (Attack)', 
            xy=(pitch_x * 0.3, arrow_y), 
            xytext=(pitch_x * 0.7, arrow_y),
            arrowprops=dict(facecolor='#71757E', edgecolor='#71757E', width=2, headwidth=8, headlength=10),
            ha='center', va='center', color='#555962', fontsize=12, fontweight='bold'
        )

    ax.set_xlim(-5, pitch_x + 5)
    ax.set_ylim(-7, pitch_y + 5)
    ax.set_aspect('equal')
    ax.axis('off')

# =========================================================
# 3. Streamlit UI 및 데이터 처리
# =========================================================
st.title("⚽ 축구 히트맵 분석기")

st.sidebar.header("📁 팀별 데이터 업로드")
st.sidebar.info("💡 팀당 1개의 전후반 통합 파일 또는 분리된 파일들을 업로드해 주세요.")

home_files = st.sidebar.file_uploader("🏠 홈팀 태깅 파일 (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)
away_files = st.sidebar.file_uploader("✈️ 어웨이팀 태깅 파일 (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)

auto_no, auto_date, auto_home, auto_away = parse_match_metadata(home_files, away_files)

st.sidebar.subheader("🏷️ 경기 정보 및 팀명 설정")
match_no_input = st.sidebar.text_input("경기 번호", value=auto_no)
match_date_input = st.sidebar.text_input("경기 날짜", value=auto_date)
home_name_input = st.sidebar.text_input("홈팀 이름 (왼쪽 팀)", value=auto_home)
away_name_input = st.sidebar.text_input("어웨이팀 이름 (오른쪽 팀)", value=auto_away)

st.sidebar.subheader("📐 경기장 규격 및 원점 설정")
pitch_x_val = st.sidebar.number_input("경기장 가로 길이 (m)", value=105.0, step=1.0)
pitch_y_val = st.sidebar.number_input("경기장 세로 길이 (m)", value=68.0, step=1.0)

flip_y_axis = st.sidebar.checkbox("↕️ Y축 상하 반전 (좌표 원점 수정용)", value=False)
auto_scale = st.sidebar.checkbox("태깅 좌표 자동 정규화 (Scaling)", value=False)

df_home = load_multiple_files(home_files)
df_away = load_multiple_files(away_files)

dfs = {}
if df_home is not None:
    dfs[home_name_input] = df_home
if df_away is not None:
    dfs[away_name_input] = df_away

sofascore_colors = [
    (0.65, 0.95, 0.70, 0.0),
    (0.60, 0.95, 0.65, 0.55),
    (0.98, 0.95, 0.45, 0.75),
    (0.95, 0.60, 0.25, 0.88),
    (0.80, 0.20, 0.20, 0.95)
]
sofascore_cmap = LinearSegmentedColormap.from_list("sofascore_style", sofascore_colors)

COLOR_PALETTES = {
    "화이트 피치 추천 (민트-노랑-빨강)": sofascore_cmap,
    "열지형 기본 (YlOrRd)": "YlOrRd",
    "레드 (강렬한 빨강)": "Reds",
    "블루 (시원한 파랑)": "Blues",
    "퍼플 (보라)": "Purples"
}

st.sidebar.subheader("🎨 팀별 옵션 (색상 / 방향 / 180° 반전)")
team_colors = {}
team_attack_dirs = {}
team_flip_option = {}

target_teams = list(dfs.keys()) if len(dfs) > 0 else [home_name_input, away_name_input]

for i, t_name in enumerate(target_teams):
    st.sidebar.markdown(f"**[{t_name}]**")
    selected_p = st.sidebar.selectbox(f"색상 테마", options=list(COLOR_PALETTES.keys()), index=0, key=f"color_{i}")
    team_colors[t_name] = COLOR_PALETTES[selected_p]
    
    dir_choice = st.sidebar.radio(
        f"전반전 공격 방향", 
        options=["왼쪽 ➔ 오른쪽", "오른쪽 ➔ 왼쪽"], 
        index=0 if i == 0 else 1,
        key=f"dir_{i}"
    )
    team_attack_dirs[t_name] = "L->R" if dir_choice == "왼쪽 ➔ 오른쪽" else "R->L"
    
    team_flip_option[t_name] = st.sidebar.checkbox(f"🔄 후반전 진영 180° 자동 반전 적용", value=False, key=f"flip_{i}")

pitch_bg = st.sidebar.color_picker("경기장 배경 색상", value="#FFFFFF")
bw_val = st.sidebar.slider("히트맵 퍼짐 정도 (부드러움)", min_value=0.2, max_value=1.0, value=0.45, step=0.05)

# =========================================================
# 4. 히트맵 시각화 및 팀별 개별 다운로드 기능
# =========================================================
st.subheader(f"📊 경기 히트맵 분석 ({pitch_x_val}m x {pitch_y_val}m 규격)")

if len(dfs) == 0:
    st.warning("⚠️ 왼쪽 사이드바에서 홈팀 또는 어웨이팀의 태깅 데이터(CSV/XLSX) 파일을 업로드해 주세요.")
else:
    tab_all, tab_first, tab_second, tab_route = st.tabs(["🔥 통합 히트맵", "⏱️ 전반전만 보기", "⏱️ 후반전만 보기", "🧭 공격 루트 시퀀스 (시작~종료)"])

    def render_heatmap(period_filter=None, route_only=False, tab_key=""):
        num_teams = len(dfs)
        if num_teams == 0:
            return

        fig_screen, axes_screen = plt.subplots(1, num_teams, figsize=(8 * num_teams, 7))
        if num_teams == 1:
            axes_screen = [axes_screen]

        vs_title = f"{home_name_input} vs {away_name_input}"

        for i, (t_name, team_df) in enumerate(dfs.items()):
            ax = axes_screen[i]
            tdf = team_df.copy()
            
            if route_only:
                tdf = extract_route_sequence(tdf)

            col_opts = tdf.columns.tolist()
            col_x = next((c for c in ['시작X', 'X좌표', 'x', 'X'] if c in col_opts), col_opts[0])
            col_y = next((c for c in ['시작Y', 'Y좌표', 'y', 'Y'] if c in col_opts), col_opts[min(1, len(col_opts)-1)])
            col_period = next((c for c in ['경기시점', 'period', 'Period', '시점'] if c in col_opts), None)

            tdf[col_x] = pd.to_numeric(tdf[col_x], errors='coerce')
            tdf[col_y] = pd.to_numeric(tdf[col_y], errors='coerce')

            if period_filter and col_period is not None:
                tdf = tdf[tdf[col_period].astype(str).str.contains(period_filter, case=False, na=False)]

            if len(tdf) == 0:
                ax.set_facecolor(pitch_bg)
                msg = f"공격 루트 (시작~종료) 구간" if route_only else f"{period_filter}"
                ax.text(pitch_x_val/2, pitch_y_val/2, f"{msg} 데이터가 존재하지 않습니다", 
                        ha='center', va='center', color='#555555', fontsize=13, fontweight='bold')
                ax.set_xlim(-5, pitch_x_val + 5)
                ax.set_ylim(-7, pitch_y_val + 5)
                ax.axis('off')
                continue

            if team_flip_option.get(t_name, False) and col_period is not None:
                second_half_mask = tdf[col_period].astype(str).str.contains('후반|2nd|Second', case=False, na=False)
                tdf.loc[second_half_mask, col_x] = pitch_x_val - tdf.loc[second_half_mask, col_x]
                tdf.loc[second_half_mask, col_y] = pitch_y_val - tdf.loc[second_half_mask, col_y]

            if flip_y_axis:
                tdf[col_y] = pitch_y_val - tdf[col_y]

            if auto_scale and tdf[col_x].max() > 0 and tdf[col_y].max() > 0:
                px = (tdf[col_x] / tdf[col_x].max()) * pitch_x_val
                py = (tdf[col_y] / tdf[col_y].max()) * pitch_y_val
            else:
                px = tdf[col_x]
                py = tdf[col_y]

            current_attack_dir = team_attack_dirs[t_name]
            if period_filter == "후반" and team_flip_option.get(t_name, False):
                current_attack_dir = "R->L" if current_attack_dir == "L->R" else "L->R"

            ax.set_facecolor(pitch_bg)

            if len(tdf) > 2:
                sns.kdeplot(
                    x=px, y=py, 
                    cmap=team_colors[t_name], 
                    fill=True, 
                    thresh=0.03,             
                    bw_adjust=bw_val,          
                    levels=60,               
                    alpha=0.85, 
                    linewidths=0,
                    ax=ax,
                    clip=((0, pitch_x_val), (0, pitch_y_val))
                )

            draw_pitch_lines(ax, pitch_x=pitch_x_val, pitch_y=pitch_y_val, line_color='#C5C8CE', attack_dir=current_attack_dir)

            ax.set_title(f"{vs_title}\n[{t_name}] 히트맵", fontsize=16, color='#222222', pad=14, fontweight='bold')

        fig_screen.patch.set_facecolor(pitch_bg)
        st.pyplot(fig_screen)

        st.markdown("### 📥 팀별 히트맵 이미지 개별 다운로드")
        col_btns = st.columns(num_teams)

        for i, (t_name, team_df) in enumerate(dfs.items()):
            with col_btns[i]:
                fig_single, ax_single = plt.subplots(1, 1, figsize=(8, 7))
                tdf = team_df.copy()
                
                if route_only:
                    tdf = extract_route_sequence(tdf)

                col_opts = tdf.columns.tolist()
                col_x = next((c for c in ['시작X', 'X좌표', 'x', 'X'] if c in col_opts), col_opts[0])
                col_y = next((c for c in ['시작Y', 'Y좌표', 'y', 'Y'] if c in col_opts), col_opts[min(1, len(col_opts)-1)])
                col_period = next((c for c in ['경기시점', 'period', 'Period', '시점'] if c in col_opts), None)

                tdf[col_x] = pd.to_numeric(tdf[col_x], errors='coerce')
                tdf[col_y] = pd.to_numeric(tdf[col_y], errors='coerce')

                if period_filter and col_period is not None:
                    tdf = tdf[tdf[col_period].astype(str).str.contains(period_filter, case=False, na=False)]

                if len(tdf) > 0:
                    if team_flip_option.get(t_name, False) and col_period is not None:
                        second_half_mask = tdf[col_period].astype(str).str.contains('후반|2nd|Second', case=False, na=False)
                        tdf.loc[second_half_mask, col_x] = pitch_x_val - tdf.loc[second_half_mask, col_x]
                        tdf.loc[second_half_mask, col_y] = pitch_y_val - tdf.loc[second_half_mask, col_y]

                    if flip_y_axis:
                        tdf[col_y] = pitch_y_val - tdf[col_y]

                    if auto_scale and tdf[col_x].max() > 0 and tdf[col_y].max() > 0:
                        px = (tdf[col_x] / tdf[col_x].max()) * pitch_x_val
                        py = (tdf[col_y] / tdf[col_y].max()) * pitch_y_val
                    else:
                        px = tdf[col_x]
                        py = tdf[col_y]

                    current_attack_dir = team_attack_dirs[t_name]
                    if period_filter == "후반" and team_flip_option.get(t_name, False):
                        current_attack_dir = "R->L" if current_attack_dir == "L->R" else "L->R"

                    ax_single.set_facecolor(pitch_bg)

                    if len(tdf) > 2:
                        sns.kdeplot(
                            x=px, y=py, 
                            cmap=team_colors[t_name], 
                            fill=True, 
                            thresh=0.03,             
                            bw_adjust=bw_val,          
                            levels=60,               
                            alpha=0.85, 
                            linewidths=0,
                            ax=ax_single,
                            clip=((0, pitch_x_val), (0, pitch_y_val))
                        )

                    draw_pitch_lines(ax_single, pitch_x=pitch_x_val, pitch_y=pitch_y_val, line_color='#C5C8CE', attack_dir=current_attack_dir)
                    ax_single.set_title(f"{vs_title}\n[{t_name}] 히트맵", fontsize=16, color='#222222', pad=14, fontweight='bold')
                    fig_single.patch.set_facecolor(pitch_bg)

                    suffix = f"_{period_filter}" if period_filter else ("_공격루트" if route_only else "")
                    download_file_name = f"{match_no_input}_{match_date_input}_{t_name}_히트맵{suffix}.png"

                    buf = io.BytesIO()
                    fig_single.savefig(buf, format="png", dpi=300, bbox_inches='tight', facecolor=fig_single.get_facecolor(), edgecolor='none')
                    buf.seek(0)

                    st.download_button(
                        label=f"📥 [{t_name}] 히트맵 다운로드",
                        data=buf,
                        file_name=download_file_name,
                        mime="image/png",
                        key=f"btn_download_{t_name}_{tab_key}"
                    )
                plt.close(fig_single)

    with tab_all:
        render_heatmap(period_filter=None, route_only=False, tab_key="all")

    with tab_first:
        render_heatmap(period_filter="전반", route_only=False, tab_key="first")

    with tab_second:
        render_heatmap(period_filter="후반", route_only=False, tab_key="second")

    with tab_route:
        render_heatmap(period_filter=None, route_only=True, tab_key="route")