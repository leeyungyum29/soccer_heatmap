#!/usr/bin/env python
# coding: utf-8

# In[8]:


import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# =========================================================
# 1. 한글 폰트 및 마이너스 기호 설정 (클라우드 배포 호환)
# =========================================================
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    # Linux / Streamlit Cloud 서버 환경용 나눔고딕 설정
    plt.rc('font', family='NanumGothic')

plt.rcParams['axes.unicode_minus'] = False

# 페이지 기본 설정
st.set_page_config(page_title="축구 팀별 맞춤 히트맵 생성기", layout="wide")

# =========================================================
# 2. 축구장 피치(105m x 68m) 그리기 함수
# =========================================================
def draw_pitch(ax, pitch_color='#7ec850', line_color='white'):
    ax.set_facecolor(pitch_color)
    
    # 외곽선 & 중앙선
    ax.plot([0, 0, 105, 105, 0], [0, 68, 68, 0, 0], color=line_color, lw=2)
    ax.plot([52.5, 52.5], [0, 68], color=line_color, lw=2)
    
    # 센터 서클 및 점
    center_circle = plt.Circle((52.5, 34), 9.15, color=line_color, fill=False, lw=2)
    ax.add_patch(center_circle)
    ax.plot(52.5, 34, 'o', color=line_color)
    
    # 페널티 박스 & 6야드 박스 (좌/우)
    ax.plot([0, 16.5, 16.5, 0], [13.84, 13.84, 54.16, 54.16], color=line_color, lw=2)
    ax.plot([0, 5.5, 5.5, 0], [24.84, 24.84, 43.16, 43.16], color=line_color, lw=2)
    ax.plot([105, 88.5, 88.5, 105], [13.84, 13.84, 54.16, 54.16], color=line_color, lw=2)
    ax.plot([105, 99.5, 99.5, 105], [24.84, 24.84, 43.16, 43.16], color=line_color, lw=2)
    
    # 골대 (좌/우)
    ax.plot([0, -2, -2, 0], [30.34, 30.34, 37.66, 37.66], color=line_color, lw=2)
    ax.plot([105, 107, 107, 105], [30.34, 30.34, 37.66, 37.66], color=line_color, lw=2)

    ax.set_xlim(-5, 110)
    ax.set_ylim(-5, 73)
    ax.set_aspect('equal')
    ax.axis('off')

# =========================================================
# 3. Streamlit UI 및 데이터 처리
# =========================================================
st.title("⚽ 축구 경기 팀별 맞춤 히트맵 생성기")
st.markdown("CSV 파일을 업로드하고 원하는 팀별 색상 테마를 선택하여 열지형 히트맵을 생성하세요.")

uploaded_file = st.sidebar.file_uploader("축구 데이터 CSV 업로드", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    st.sidebar.info("CSV 파일을 업로드하지 않으면 테스트용 샘플 데이터가 표시됩니다.")
    np.random.seed(42)
    n = 300
    df_a = pd.DataFrame({'x': np.random.beta(3, 2, n)*105, 'y': np.random.normal(34, 12, n).clip(0,68), 'team': 'FC RED'})
    df_b = pd.DataFrame({'x': np.random.beta(2, 3, n)*105, 'y': np.random.normal(20, 10, n).clip(0,68), 'team': 'FC BLUE'})
    df = pd.concat([df_a, df_b], ignore_index=True)

st.sidebar.subheader("📌 데이터 컬럼 설정")
col_options = df.columns.tolist()

col_x = st.sidebar.selectbox("X 좌표 컬럼", col_options, index=col_options.index('x') if 'x' in col_options else 0)
col_y = st.sidebar.selectbox("Y 좌표 컬럼", col_options, index=col_options.index('y') if 'y' in col_options else 1)
col_team = st.sidebar.selectbox("팀 이름 컬럼", col_options, index=col_options.index('team') if 'team' in col_options else 2)

teams = df[col_team].unique()

COLOR_PALETTES = {
    "열지형 (초록-노랑-빨강)": "YlOrRd",
    "레드 (강렬한 빨강)": "Reds",
    "블루 (시원한 파랑)": "Blues",
    "퍼플 (보라)": "Purples",
    "오렌지 (주황)": "Oranges",
    "핫/불꽃 (Black-Red-Yellow)": "hot",
    "플라즈마 (Plasma)": "plasma"
}

if len(teams) < 1:
    st.error("팀 데이터가 없습니다.")
else:
    st.sidebar.subheader("🎨 팀별 히트맵 색상 커스텀")
    team_colors = {}
    
    for i, team in enumerate(teams[:2]):
        default_index = 0 if i == 0 else 2
        selected_palette = st.sidebar.selectbox(
            f"[{team}] 색상 테마 선택",
            options=list(COLOR_PALETTES.keys()),
            index=default_index
        )
        team_colors[team] = COLOR_PALETTES[selected_palette]

    pitch_bg = st.sidebar.color_picker("경기장 잔디 색상 선택", value="#7EC850")

    st.subheader("📊 팀별 피치 점유 히트맵")
    
    fig, axes = plt.subplots(1, min(2, len(teams)), figsize=(16, 7))
    if len(teams) == 1:
        axes = [axes]

    for i, team in enumerate(teams[:2]):
        ax = axes[i]
        team_df = df[df[col_team] == team]
        
        draw_pitch(ax, pitch_color=pitch_bg)
        
        # 빈도가 높을수록 색상이 진해지는 연속 KDE 연무형 히트맵
        sns.kdeplot(
            data=team_df, x=col_x, y=col_y, 
            cmap=team_colors[team], fill=True, thresh=0.03, 
            levels=30, alpha=0.75, ax=ax
        )

        ax.set_title(f"[{team}] 히트맵 (데이터 수: {len(team_df)}개)", fontsize=14, color='white', pad=10, fontweight='bold')

    fig.patch.set_facecolor('#1e1e1e')
    st.pyplot(fig)

    st.subheader("📋 업로드된 데이터 미리보기")
    st.dataframe(df.head(10))

