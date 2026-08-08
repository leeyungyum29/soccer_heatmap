import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import platform

# =========================================================
# 1. 한글 및 영문 폰트 가독성 / 깨짐 방지 설정
# =========================================================
def set_korean_font():
    sys_name = platform.system()
    if sys_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif sys_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        # Streamlit Cloud (Linux) 및 외부 환경 대응
        font_list = [f.name for f in fm.fontManager.ttflist]
        if 'NanumGothic' in font_list:
            plt.rc('font', family='NanumGothic')
        else:
            plt.rc('font', family='DejaVu Sans')

set_korean_font()
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="축구 팀별 맞춤 히트맵 분석기", layout="wide")

# =========================================================
# 2. 맞춤 축구장 피치(95m x 57m 기본값) 그리기 함수
# =========================================================
def draw_pitch(ax, pitch_x=95.0, pitch_y=57.0, pitch_color='#7ec850', line_color='white'):
    ax.set_facecolor(pitch_color)
    
    # 외곽선 및 중앙선
    ax.plot([0, 0, pitch_x, pitch_x, 0], [0, pitch_y, pitch_y, 0, 0], color=line_color, lw=2)
    ax.plot([pitch_x/2, pitch_x/2], [0, pitch_y], color=line_color, lw=2)
    
    # 센터 서클
    center_circle = plt.Circle((pitch_x/2, pitch_y/2), 9.15, color=line_color, fill=False, lw=2)
    ax.add_patch(center_circle)
    ax.plot(pitch_x/2, pitch_y/2, 'o', color=line_color)
    
    # 페널티 박스 (비율 자동 계산)
    box_y_bottom = (pitch_y - 40.32) / 2
    box_y_top = (pitch_y + 40.32) / 2
    goal_y_bottom = (pitch_y - 18.32) / 2
    goal_y_top = (pitch_y + 18.32) / 2
    
    # 좌우 페널티 박스
    ax.plot([0, 16.5, 16.5, 0], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2)
    ax.plot([0, 5.5, 5.5, 0], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2)
    
    ax.plot([pitch_x, pitch_x - 16.5, pitch_x - 16.5, pitch_x], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2)
    ax.plot([pitch_x, pitch_x - 5.5, pitch_x - 5.5, pitch_x], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2)
    
    # 골대
    ax.plot([0, -2, -2, 0], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color=line_color, lw=2)
    ax.plot([pitch_x, pitch_x + 2, pitch_x + 2, pitch_x], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color=line_color, lw=2)

    ax.set_xlim(-5, pitch_x + 5)
    ax.set_ylim(-5, pitch_y + 5)
    ax.set_aspect('equal')
    ax.axis('off')

# 파일 로드 도우미 함수
def load_data(file):
    if file is None:
        return None
    if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
        return pd.read_excel(file)
    else:
        return pd.read_csv(file)

# =========================================================
# 3. Streamlit UI 및 데이터 처리
# =========================================================
st.title("⚽ 홈/어웨이 파일 분리 지원 축구 히트맵 분석기")

st.sidebar.header("📁 데이터 업로드")
home_file = st.sidebar.file_uploader("🏠 홈팀 태깅 데이터 (CSV/XLSX)", type=["csv", "xlsx"])
away_file = st.sidebar.file_uploader("✈️ 어웨이팀 태깅 데이터 (CSV/XLSX)", type=["csv", "xlsx"])

# 홈/어웨이 팀명 직접 입력 옵션
st.sidebar.subheader("🏷️ 팀명 직접 지정 (선택사항)")
home_name_input = st.sidebar.text_input("홈팀 이름 (Home Team)", value="Home Team")
away_name_input = st.sidebar.text_input("어웨이팀 이름 (Away Team)", value="Away Team")

st.sidebar.subheader("📐 경기장 규격 설정")
pitch_x_val = st.sidebar.number_input("경기장 가로 길이 (m)", value=95.0, step=1.0)
pitch_y_val = st.sidebar.number_input("경기장 세로 길이 (m)", value=57.0, step=1.0)
auto_scale = st.sidebar.checkbox("태깅 좌표 자동 정규화 (Scaling)", value=False)

# 데이터프레임 구성
df_home = load_data(home_file)
df_away = load_data(away_file)

# 샘플 데이터 생성 (파일 없을 경우)
if df_home is None and df_away is None:
    st.sidebar.info("파일을 업로드하면 홈/어웨이 각각 개별 히트맵이 생성됩니다. (현재 샘플 데이터 표시 중)")
    np.random.seed(42)
    n = 200
    df_home = pd.DataFrame({'X좌표': np.random.beta(3, 2, n)*95, 'Y좌표': np.random.normal(28.5, 10, n).clip(0,57), '이벤트': np.random.choice(['패스 성공', '슈팅'], n)})
    df_away = pd.DataFrame({'X좌표': np.random.beta(2, 3, n)*95, 'Y좌표': np.random.normal(20, 8, n).clip(0,57), '이벤트': np.random.choice(['패스 성공', '인터셉트'], n)})

# 데이터 매핑 및 처리
dfs = {}
if df_home is not None:
    dfs[home_name_input] = df_home
if df_away is not None:
    dfs[away_name_input] = df_away

# 색상 테마 정의
COLOR_PALETTES = {
    "열지형 (초록-노랑-빨강)": "YlOrRd",
    "레드 (강렬한 빨강)": "Reds",
    "블루 (시원한 파랑)": "Blues",
    "퍼플 (보라)": "Purples",
    "오렌지 (주황)": "Oranges",
    "불꽃 (hot)": "hot"
}

st.sidebar.subheader("🎨 팀별 히트맵 색상 지정")
team_colors = {}
for i, (t_name, _) in enumerate(dfs.items()):
    default_idx = 0 if i == 0 else 2
    selected_p = st.sidebar.selectbox(f"[{t_name}] 색상 테마", options=list(COLOR_PALETTES.keys()), index=default_idx)
    team_colors[t_name] = COLOR_PALETTES[selected_p]

pitch_bg = st.sidebar.color_picker("경기장 잔디 색상", value="#7EC850")

# 히트맵 시각화
st.subheader(f"📊 경기 히트맵 분석 ({pitch_x_val}m x {pitch_y_val}m 규격)")

num_teams = len(dfs)
if num_teams > 0:
    fig, axes = plt.subplots(1, num_teams, figsize=(8 * num_teams, 7))
    if num_teams == 1:
        axes = [axes]

    for i, (t_name, team_df) in enumerate(dfs.items()):
        ax = axes[i]
        
        # 컬럼 자동 매핑
        col_opts = team_df.columns.tolist()
        col_x = next((c for c in ['X좌표', 'x', 'X'] if c in col_opts), col_opts[0])
        col_y = next((c for c in ['Y좌표', 'y', 'Y'] if c in col_opts), col_opts[min(1, len(col_opts)-1)])
        
        # 정규화 옵션
        if auto_scale and team_df[col_x].max() > 0 and team_df[col_y].max() > 0:
            px = (team_df[col_x] / team_df[col_x].max()) * pitch_x_val
            py = (team_df[col_y] / team_df[col_y].max()) * pitch_y_val
        else:
            px = team_df[col_x]
            py = team_df[col_y]

        draw_pitch(ax, pitch_x=pitch_x_val, pitch_y=pitch_y_val, pitch_color=pitch_bg)

        if len(team_df) > 2:
            sns.kdeplot(
                x=px, y=py, 
                cmap=team_colors[t_name], fill=True, thresh=0.03, 
                levels=30, alpha=0.75, ax=ax
            )

        # 영문/한글 제목 표시 가독성 강화
        ax.set_title(f"[{t_name}] 히트맵 (이벤트: {len(team_df)}개)", fontsize=14, color='white', pad=12, fontweight='bold')

    fig.patch.set_facecolor('#1e1e1e')
    st.pyplot(fig)
