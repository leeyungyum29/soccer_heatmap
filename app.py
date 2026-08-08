import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# =========================================================
# 1. 한글 폰트 설정
# =========================================================
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    plt.rc('font', family='NanumGothic')

plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="축구 팀별 맞춤 히트맵 생성기", layout="wide")

# =========================================================
# 2. 맞춤 축구장 피치(95m x 57m) 그리기 함수
# =========================================================
def draw_pitch(ax, pitch_x=95.0, pitch_y=57.0, pitch_color='#7ec850', line_color='white'):
    ax.set_facecolor(pitch_color)
    
    # 외곽선 및 중앙선
    ax.plot([0, 0, pitch_x, pitch_x, 0], [0, pitch_y, pitch_y, 0, 0], color=line_color, lw=2)
    ax.plot([pitch_x/2, pitch_x/2], [0, pitch_y], color=line_color, lw=2)
    
    # 센터 서클 (규격 비율 적용)
    center_circle = plt.Circle((pitch_x/2, pitch_y/2), 9.15, color=line_color, fill=False, lw=2)
    ax.add_patch(center_circle)
    ax.plot(pitch_x/2, pitch_y/2, 'o', color=line_color)
    
    # 페널티 박스 (규격 비율 적용)
    box_y_bottom = (pitch_y - 40.32) / 2
    box_y_top = (pitch_y + 40.32) / 2
    goal_y_bottom = (pitch_y - 18.32) / 2
    goal_y_top = (pitch_y + 18.32) / 2
    
    # 왼쪽 페널티 박스 & 6야드 박스
    ax.plot([0, 16.5, 16.5, 0], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2)
    ax.plot([0, 5.5, 5.5, 0], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2)
    
    # 오른쪽 페널티 박스 & 6야드 박스
    ax.plot([pitch_x, pitch_x - 16.5, pitch_x - 16.5, pitch_x], [box_y_bottom, box_y_bottom, box_y_top, box_y_top], color=line_color, lw=2)
    ax.plot([pitch_x, pitch_x - 5.5, pitch_x - 5.5, pitch_x], [goal_y_bottom, goal_y_bottom, goal_y_top, goal_y_top], color=line_color, lw=2)
    
    # 골대
    ax.plot([0, -2, -2, 0], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color=line_color, lw=2)
    ax.plot([pitch_x, pitch_x + 2, pitch_x + 2, pitch_x], [pitch_y/2 - 3.66, pitch_y/2 - 3.66, pitch_y/2 + 3.66, pitch_y/2 + 3.66], color=line_color, lw=2)

    ax.set_xlim(-5, pitch_x + 5)
    ax.set_ylim(-5, pitch_y + 5)
    ax.set_aspect('equal')
    ax.axis('off')

# =========================================================
# 3. 데이터 로드 및 UI 구성
# =========================================================
st.title("⚽ 경기장 규격 맞춤형 팀별 히트맵 생성기")

uploaded_file = st.sidebar.file_uploader("태깅 데이터 업로드 (CSV / XLSX)", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
else:
    st.sidebar.info("파일을 업로드하면 자동으로 분석이 진행됩니다.")
    np.random.seed(42)
    n = 300
    df = pd.DataFrame({
        'X좌표': np.random.beta(3, 2, n)*95, 
        'Y좌표': np.random.normal(28.5, 10, n).clip(0,57), 
        '팀명': np.random.choice(['Home', 'Away'], n),
        '이벤트': np.random.choice(['패스 성공', '슈팅', '획득'], n)
    })

st.sidebar.subheader("📐 경기장 규격 설정")
pitch_x_val = st.sidebar.number_input("경기장 가로 길이 (m)", value=95.0, step=1.0)
pitch_y_val = st.sidebar.number_input("경기장 세로 길이 (m)", value=57.0, step=1.0)

auto_scale = st.sidebar.checkbox("태깅 좌표를 경기장 규격으로 자동 정규화(Scaling)", value=False)

st.sidebar.subheader("📌 컬럼 자동 매핑")
col_options = df.columns.tolist()

default_x = next((c for c in ['X좌표', 'x', 'X'] if c in col_options), col_options[0])
default_y = next((c for c in ['Y좌표', 'y', 'Y'] if c in col_options), col_options[min(1, len(col_options)-1)])
default_team = next((c for c in ['팀명', 'team', 'Team'] if c in col_options), col_options[min(2, len(col_options)-1)])

col_x = st.sidebar.selectbox("X 좌표 컬럼", col_options, index=col_options.index(default_x))
col_y = st.sidebar.selectbox("Y 좌표 컬럼", col_options, index=col_options.index(default_y))
col_team = st.sidebar.selectbox("팀 이름 컬럼", col_options, index=col_options.index(default_team))

# 자동 스케일링 옵션 적용
if auto_scale:
    max_x = df[col_x].max()
    max_y = df[col_y].max()
    if max_x > 0 and max_y > 0:
        df['X_scaled'] = (df[col_x] / max_x) * pitch_x_val
        df['Y_scaled'] = (df[col_y] / max_y) * pitch_y_val
        plot_x = 'X_scaled'
        plot_y = 'Y_scaled'
    else:
        plot_x = col_x
        plot_y = col_y
else:
    plot_x = col_x
    plot_y = col_y

if '이벤트' in col_options:
    events = ['전체 (All)'] + list(df['이벤트'].dropna().unique())
    selected_event = st.sidebar.selectbox("이벤트 필터", events)
    if selected_event != '전체 (All)':
        df = df[df['이벤트'] == selected_event]

teams = df[col_team].dropna().unique()

COLOR_PALETTES = {
    "열지형 (초록-노랑-빨강)": "YlOrRd",
    "레드 (강렬한 빨강)": "Reds",
    "블루 (시원한 파랑)": "Blues",
    "퍼플 (보라)": "Purples",
    "오렌지 (주황)": "Oranges",
    "불꽃 (hot)": "hot"
}

if len(teams) >= 1:
    st.sidebar.subheader("🎨 팀별 색상 테마")
    team_colors = {}
    for i, team in enumerate(teams[:2]):
        selected_palette = st.sidebar.selectbox(
            f"[{team}] 색상 테마",
            options=list(COLOR_PALETTES.keys()),
            index=0 if i == 0 else 2
        )
        team_colors[team] = COLOR_PALETTES[selected_palette]

    pitch_bg = st.sidebar.color_picker("경기장 잔디 색상", value="#7EC850")

    st.subheader(f"📊 팀별 피치 점유 히트맵 ({pitch_x_val}m x {pitch_y_val}m 규격)")
    
    fig, axes = plt.subplots(1, min(2, len(teams)), figsize=(16, 7))
    if len(teams) == 1:
        axes = [axes]

    for i, team in enumerate(teams[:2]):
        ax = axes[i]
        team_df = df[df[col_team] == team]
        
        draw_pitch(ax, pitch_x=pitch_x_val, pitch_y=pitch_y_val, pitch_color=pitch_bg)
        
        if len(team_df) > 2:
            sns.kdeplot(
                data=team_df, x=plot_x, y=plot_y, 
                cmap=team_colors[team], fill=True, thresh=0.03, 
                levels=30, alpha=0.75, ax=ax
            )

        ax.set_title(f"[{team}] 히트맵 (이벤트 수: {len(team_df)}개)", fontsize=14, color='white', pad=10, fontweight='bold')

    fig.patch.set_facecolor('#1e1e1e')
    st.pyplot(fig)

    st.subheader("📋 업로드된 데이터 미리보기")
    st.dataframe(df.head(10))
