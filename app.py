import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform
import os
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

# =========================================================
# 2. 맞춤 축구장 피치(105m x 68m 기본값) 및 공격 방향 화살표 그리기
# =========================================================
def draw_pitch_lines(ax, pitch_x=105.0, pitch_y=68.0, line_color='white', attack_dir="L->R"):
    # 외곽선 및 중앙선
    ax.plot([0, 0, pitch_x, pitch_x, 0], [0, pitch_y, pitch_y, 0, 0], color=line_color, lw=2)
    ax.plot([pitch_x/2, pitch_x/2], [0, pitch_y], color=line_color, lw=2)
    
    # 센터 서클
    center_circle = plt.Circle((pitch_x/2, pitch_y/2), 9.15, color=line_color, fill=False, lw=2)
    ax.add_patch(center_circle)
    ax.plot(pitch_x/2, pitch_y/2, 'o', color=line_color)
    
    # 페널티 박스
    box_y_bottom = (pitch_y - 40.32) / 2
    box_y_top = (pitch_y + 40.32) / 2
    goal_y_bottom = (pitch_y - 18.32) / 2
    goal_y_top = (pitch_y + 18.32) / 2
    
    ax.plot([0, 16.5, 16.5, 0], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2)
    ax.plot([0, 5.5, 5.5, 0], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2)
    
    ax.plot([pitch_x, pitch_x - 16.5, pitch_x - 16.5, pitch_x], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2)
    ax.plot([pitch_x, pitch_x - 5.5, pitch_x - 5.5, pitch_x], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2)
    
    # 골대
    ax.plot([0, -2, -2, 0], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color=line_color, lw=2)
    ax.plot([pitch_x, pitch_x + 2, pitch_x + 2, pitch_x], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color=line_color, lw=2)

    # 공격 방향 화살표 표시
    arrow_y = -3.5
    if attack_dir == "L->R":
        ax.annotate(
            '공격 방향 (Attack) ▶', 
            xy=(pitch_x * 0.7, arrow_y), 
            xytext=(pitch_x * 0.3, arrow_y),
            arrowprops=dict(facecolor='white', edgecolor='white', width=2, headwidth=8, headlength=10),
            ha='center', va='center', color='white', fontsize=11, fontweight='bold'
        )
    else:
        ax.annotate(
            '◀ 공격 방향 (Attack)', 
            xy=(pitch_x * 0.3, arrow_y), 
            xytext=(pitch_x * 0.7, arrow_y),
            arrowprops=dict(facecolor='white', edgecolor='white', width=2, headwidth=8, headlength=10),
            ha='center', va='center', color='white', fontsize=11, fontweight='bold'
        )

    ax.set_xlim(-5, pitch_x + 5)
    ax.set_ylim(-7, pitch_y + 5)
    ax.set_aspect('equal')
    ax.axis('off')

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
# 3. Streamlit UI 및 데이터 처리
# =========================================================
st.title("⚽ 축구 히트맵 분석기")

st.sidebar.header("📁 팀별 데이터 업로드")
st.sidebar.info("💡 팀당 1개의 전후반 통합 파일 또는 분리된 파일들을 업로드해 주세요.")

home_files = st.sidebar.file_uploader("🏠 홈팀 태깅 파일 (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)
away_files = st.sidebar.file_uploader("✈️ 어웨이팀 태깅 파일 (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)

st.sidebar.subheader("🏷️ 팀명 직접 지정")
home_name_input = st.sidebar.text_input("홈팀 이름 (Home Team)", value="Home Team")
away_name_input = st.sidebar.text_input("어웨이팀 이름 (Away Team)", value="Away Team")

st.sidebar.subheader("📐 경기장 규격 및 진영 설정")
pitch_x_val = st.sidebar.number_input("경기장 가로 길이 (m)", value=105.0, step=1.0)
pitch_y_val = st.sidebar.number_input("경기장 세로 길이 (m)", value=68.0, step=1.0)

flip_second_half = st.sidebar.checkbox("🔄 후반전 진영 180° 자동 반전 (필요 시 체크)", value=False)
flip_y_axis = st.sidebar.checkbox("↕️ Y축 상하 반전 (좌표 원점 수정용)", value=False)
auto_scale = st.sidebar.checkbox("태깅 좌표 자동 정규화 (Scaling)", value=False)

df_home = load_multiple_files(home_files)
df_away = load_multiple_files(away_files)

dfs = {}
if df_home is not None:
    dfs[home_name_input] = df_home
if df_away is not None:
    dfs[away_name_input] = df_away

# 초록 피치 전용 노랑-주황-빨강 커스텀 컬러맵
green_heatmap_colors = [(0.9, 0.9, 0.4, 0.0), (1.0, 0.8, 0.2, 0.6), (1.0, 0.5, 0.0, 0.8), (0.9, 0.1, 0.1, 0.95)]
green_cmap = LinearSegmentedColormap.from_list("green_pitch_heatmap", green_heatmap_colors)

COLOR_PALETTES = {
    "열지형 (초록 피치 추천: 노랑-주황-빨강)": green_cmap,
    "열지형 기본 (YlOrRd)": "YlOrRd",
    "레드 (강렬한 빨강)": "Reds",
    "블루 (시원한 파랑)": "Blues",
    "퍼플 (보라)": "Purples",
    "불꽃 (hot)": "hot"
}

st.sidebar.subheader("🎨 팀별 히트맵 색상 및 디자인")
team_colors = {}
team_attack_dirs = {}

target_teams = list(dfs.keys()) if len(dfs) > 0 else [home_name_input, away_name_input]

for i, t_name in enumerate(target_teams):
    default_idx = 0
    selected_p = st.sidebar.selectbox(f"[{t_name}] 색상 테마", options=list(COLOR_PALETTES.keys()), index=default_idx, key=f"color_{i}")
    team_colors[t_name] = COLOR_PALETTES[selected_p]
    
    dir_choice = st.sidebar.radio(
        f"[{t_name}] 전반전 공격 방향", 
        options=["왼쪽 ➔ 오른쪽", "오른쪽 ➔ 왼쪽"], 
        index=0 if i == 0 else 1,
        key=f"dir_{i}"
    )
    team_attack_dirs[t_name] = "L->R" if dir_choice == "왼쪽 ➔ 오른쪽" else "R->L"

pitch_bg = st.sidebar.color_picker("경기장 잔디 색상", value="#1E4D2B")
bw_val = st.sidebar.slider("히트맵 퍼짐 정도 (부드러움)", min_value=0.2, max_value=1.0, value=0.50, step=0.05)

# =========================================================
# 4. 히트맵 시각화 (통합 / 전반 / 후반 / 공격 루트 시퀀스)
# =========================================================
st.subheader(f"📊 경기 히트맵 분석 ({pitch_x_val}m x {pitch_y_val}m 규격)")

if len(dfs) == 0:
    st.warning("⚠️ 왼쪽 사이드바에서 홈팀 또는 어웨이팀의 태깅 데이터(CSV/XLSX) 파일을 업로드해 주세요.")
else:
    tab_all, tab_first, tab_second, tab_route = st.tabs(["🔥 통합 히트맵", "⏱️ 전반전만 보기", "⏱️ 후반전만 보기", "🧭 공격 루트 시퀀스 (시작~종료)"])

    def render_heatmap(period_filter=None, route_only=False):
        num_teams = len(dfs)
        if num_teams == 0:
            return

        fig, axes = plt.subplots(1, num_teams, figsize=(8 * num_teams, 7))
        if num_teams == 1:
            axes = [axes]

        for i, (t_name, team_df) in enumerate(dfs.items()):
            ax = axes[i]
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
                        ha='center', va='center', color='white', fontsize=12, fontweight='bold')
                ax.set_xlim(-5, pitch_x_val + 5)
                ax.set_ylim(-7, pitch_y_val + 5)
                ax.axis('off')
                continue

            if flip_second_half and col_period is not None:
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
            if period_filter == "후반" and flip_second_half:
                current_attack_dir = "R->L" if current_attack_dir == "L->R" else "L->R"

            # 핵심: 서브플롯(ax) 배경색과 전체 그림(fig) 배경색을 사용자가 지정한 초록 잔디색(pitch_bg)으로 일치시킴
            ax.set_facecolor(pitch_bg)

            # 1. 히트맵 렌더링
            if len(tdf) > 2:
                sns.kdeplot(
                    x=px, y=py, 
                    cmap=team_colors[t_name], 
                    fill=True, 
                    thresh=0.05,             
                    bw_adjust=bw_val,          
                    levels=50,               
                    alpha=0.80, 
                    linewidths=0,
                    ax=ax,
                    clip=((0, pitch_x_val), (0, pitch_y_val))
                )

            # 2. 피치 라인 그리기
            draw_pitch_lines(ax, pitch_x=pitch_x_val, pitch_y=pitch_y_val, line_color='white', attack_dir=current_attack_dir)

            ax.set_title(f"[{t_name}] 히트맵", fontsize=14, color='white', pad=12, fontweight='bold')

        fig.patch.set_facecolor(pitch_bg)
        st.pyplot(fig)

    with tab_all:
        render_heatmap(period_filter=None, route_only=False)

    with tab_first:
        render_heatmap(period_filter="전반", route_only=False)

    with tab_second:
        render_heatmap(period_filter="후반", route_only=False)

    with tab_route:
        render_heatmap(period_filter=None, route_only=True)
