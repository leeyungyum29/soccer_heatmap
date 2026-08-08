import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform
import os
import urllib.request

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
# 2. 맞춤 축구장 피치(95m x 57m 기본값) 및 공격 방향 화살표 그리기
# =========================================================
def draw_pitch(ax, pitch_x=95.0, pitch_y=57.0, pitch_color='#7ec850', line_color='white', attack_dir="L->R"):
    ax.set_facecolor(pitch_color)
    
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

# 다중 파일 로드 및 통합 도우미 함수
def load_multiple_files(files):
    if not files:
        return None
    df_list = []
    for file in files:
        if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
            temp_df = pd.read_excel(file)
        else:
            temp_df = pd.read_csv(file)
        
        # 파일명에 '전반' / '후반' 문구가 있으면 경기시점 컬럼 자동 부여
        if '경기시점' not in temp_df.columns:
            if '전반' in file.name:
                temp_df['경기시점'] = '전반전'
            elif '후반' in file.name:
                temp_df['경기시점'] = '후반전'
        df_list.append(temp_df)
    
    return pd.concat(df_list, ignore_index=True) if df_list else None

# =========================================================
# 3. Streamlit UI 및 데이터 처리
# =========================================================
st.title("⚽ 전/후반 자동 진영 통일 축구 히트맵 분석기")

st.sidebar.header("📁 팀별 데이터 업로드 (드래그 & 드롭)")
st.sidebar.info("💡 팀당 전반/후반 2개 파일을 한 번에 복수 선택해서 올려주세요.")

home_files = st.sidebar.file_uploader("🏠 홈팀 태깅 파일들 (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)
away_files = st.sidebar.file_uploader("✈️ 어웨이팀 태깅 파일들 (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)

st.sidebar.subheader("🏷️ 팀명 직접 지정")
home_name_input = st.sidebar.text_input("홈팀 이름 (Home Team)", value="Home Team")
away_name_input = st.sidebar.text_input("어웨이팀 이름 (Away Team)", value="Away Team")

st.sidebar.subheader("📐 경기장 규격 및 진영 설정")
pitch_x_val = st.sidebar.number_input("경기장 가로 길이 (m)", value=95.0, step=1.0)
pitch_y_val = st.sidebar.number_input("경기장 세로 길이 (m)", value=57.0, step=1.0)
flip_second_half = st.sidebar.checkbox("🔄 후반전 진영 180° 자동 반전 (X, Y축 모두 반전)", value=True)
flip_y_axis = st.sidebar.checkbox("↕️ Y축 상하 반전 (좌표 원점 수정용)", value=False)
auto_scale = st.sidebar.checkbox("태깅 좌표 자동 정규화 (Scaling)", value=False)

df_home = load_multiple_files(home_files)
df_away = load_multiple_files(away_files)

# 샘플 데이터 생성
if df_home is None and df_away is None:
    np.random.seed(42)
    n = 200
    df_home = pd.DataFrame({'X좌표': np.random.beta(3, 2, n)*95, 'Y좌표': np.random.normal(28.5, 10, n).clip(0,57), '경기시점': ['전반전']*100 + ['후반전']*100})
    df_away = pd.DataFrame({'X좌표': np.random.beta(2, 3, n)*95, 'Y좌표': np.random.normal(20, 8, n).clip(0,57), '경기시점': ['전반전']*100 + ['후반전']*100})

dfs = {}
if df_home is not None:
    dfs[home_name_input] = df_home
if df_away is not None:
    dfs[away_name_input] = df_away

COLOR_PALETTES = {
    "열지형 (초록-노랑-빨강)": "YlOrRd",
    "레드 (강렬한 빨강)": "Reds",
    "블루 (시원한 파랑)": "Blues",
    "퍼플 (보라)": "Purples",
    "오렌지 (주황)": "Oranges",
    "불꽃 (hot)": "hot"
}

st.sidebar.subheader("🎨 팀별 히트맵 색상 및 방향")
team_colors = {}
team_attack_dirs = {}

for i, (t_name, _) in enumerate(dfs.items()):
    default_idx = 0 if i == 0 else 2
    selected_p = st.sidebar.selectbox(f"[{t_name}] 색상 테마", options=list(COLOR_PALETTES.keys()), index=default_idx, key=f"color_{i}")
    team_colors[t_name] = COLOR_PALETTES[selected_p]
    
    dir_choice = st.sidebar.radio(
        f"[{t_name}] 전반전 공격 방향", 
        options=["왼쪽 ➔ 오른쪽", "오른쪽 ➔ 왼쪽"], 
        index=0 if i == 0 else 1,
        key=f"dir_{i}"
    )
    team_attack_dirs[t_name] = "L->R" if dir_choice == "왼쪽 ➔ 오른쪽" else "R->L"

pitch_bg = st.sidebar.color_picker("경기장 잔디 색상", value="#7EC850")

# =========================================================
# 4. 히트맵 시각화 (탭 분리: 통합 / 전반전 / 후반전)
# =========================================================
st.subheader(f"📊 경기 히트맵 분석 ({pitch_x_val}m x {pitch_y_val}m 규격)")
tab_all, tab_first, tab_second = st.tabs(["🔥 통합 히트맵", "⏱️ 전반전만 보기", "⏱️ 후반전만 보기"])

def render_heatmap(period_filter=None):
    num_teams = len(dfs)
    if num_teams == 0:
        return

    fig, axes = plt.subplots(1, num_teams, figsize=(8 * num_teams, 7))
    if num_teams == 1:
        axes = [axes]

    for i, (t_name, team_df) in enumerate(dfs.items()):
        ax = axes[i]
        tdf = team_df.copy()
        
        col_opts = tdf.columns.tolist()
        col_x = next((c for c in ['X좌표', 'x', 'X'] if c in col_opts), col_opts[0])
        col_y = next((c for c in ['Y좌표', 'y', 'Y'] if c in col_opts), col_opts[min(1, len(col_opts)-1)])
        col_period = next((c for c in ['경기시점', 'period', 'Period'] if c in col_opts), None)

        # 기간 필터링 적용
        if period_filter and col_period is not None:
            tdf = tdf[tdf[col_period].astype(str).str.contains(period_filter, case=False, na=False)]

        if len(tdf) == 0:
            ax.set_facecolor(pitch_bg)
            ax.text(pitch_x_val/2, pitch_y_val/2, f"{period_filter} 태깅 데이터를 업로드해 주세요", 
                    ha='center', va='center', color='white', fontsize=12, fontweight='bold')
            ax.set_xlim(-5, pitch_x_val + 5)
            ax.set_ylim(-7, pitch_y_val + 5)
            ax.axis('off')
            continue

        # 후반전 진영 180도 자동 반전 (통합/후반 탭 시 적용)
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

        # 공격 방향 지정 (후반전만 볼 때는 공격 방향 반전 표시)
        current_attack_dir = team_attack_dirs[t_name]
        if period_filter == "후반" and not flip_second_half:
            current_attack_dir = "R->L" if current_attack_dir == "L->R" else "L->R"

        draw_pitch(ax, pitch_x=pitch_x_val, pitch_y=pitch_y_val, pitch_color=pitch_bg, attack_dir=current_attack_dir)

        if len(tdf) > 2:
            sns.kdeplot(x=px, y=py, cmap=team_colors[t_name], fill=True, thresh=0.03, levels=30, alpha=0.75, ax=ax)

        ax.set_title(f"[{t_name}] 히트맵 (이벤트: {len(tdf)}개)", fontsize=14, color='white', pad=12, fontweight='bold')

    fig.patch.set_facecolor('#1e1e1e')
    st.pyplot(fig)

with tab_all:
    render_heatmap(period_filter=None)

with tab_first:
    render_heatmap(period_filter="전반")

with tab_second:
    render_heatmap(period_filter="후반")
