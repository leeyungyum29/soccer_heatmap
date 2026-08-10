# 기존 kdeplot 수정을 통한 스타일 변경
if len(tdf) > 2:
    sns.kdeplot(
        x=px, y=py, 
        cmap=team_colors[t_name], 
        fill=True, 
        thresh=0.08,             # 낮은 밀도 구간을 투명 처리하여 잔디 배경 노출
        bw_adjust=0.35,          # 세밀한 구름 입자 형태로 좁게 뭉치도록 설정
        levels=40,               # 색상 단계를 촘촘하게 설정
        alpha=0.85, 
        ax=ax,
        clip=((0, pitch_x_val), (0, pitch_y_val)) # 피치 라인 내부로 클리핑
    )