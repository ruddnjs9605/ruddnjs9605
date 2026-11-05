# 루퍼트의 눈물 — 코드로 만든 모션 그래픽 (릴스용)

그림 AI·영상 AI 없이 SVG 코드로 장면을 그리고, 효과음도 코드로 합성해 만든 28.5초 세로 영상(1080×1920, 30fps)입니다.

- 완성본: `rupert_drop_reels.mp4` (효과음 포함, 내레이션 없음)

## 파일

| 파일 | 역할 |
|---|---|
| `index.html` | 모든 장면. `render(frame)` 이 프레임 번호를 받아 그 순간의 SVG 를 그립니다 |
| `render.js` | Playwright(Chromium)로 프레임을 한 장씩 찍어 FFmpeg 로 넘깁니다 |
| `audio.py` | 망치·균열·폭발·물소리·배경음을 numpy 로 합성해 WAV 로 저장합니다 |

## 다시 만들기

필요한 것: Node.js, `playwright`(Chromium 포함), FFmpeg, Python 3 + numpy

```bash
python3 audio.py audio.wav
node render.js video.mp4                 # 855프레임, 수 분 걸림
ffmpeg -y -i video.mp4 -i audio.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart rupert_drop_reels.mp4

# 장면 확인용 정지 화면만 뽑기 (still_<프레임>.png)
node render.js - 60,175,560,690
```

## 장면 구성

| 시간 | 장면 |
|---|---|
| 0–4초 | 망치로 내리쳐도 멀쩡 |
| 4–7.6초 | 꼬리를 꺾자 균열 → 폭발 |
| 7.6–11초 | 제목: 루퍼트의 눈물 |
| 11–15.6초 | 만드는 법: 녹인 유리 → 찬물 |
| 15.6–21초 | 단면: 겉 압축 / 속 인장, 약 700MPa |
| 21–25초 | 균열 속도 초속 약 1.5km (슬로 모션) |
| 25–28.5초 | 강화유리도 같은 원리 |

장면 시각은 `index.html` 의 `SCENES` 와 `audio.py` 의 이벤트 시각이 서로 맞춰져 있으니, 한쪽을 바꾸면 다른 쪽도 같이 바꾸세요.

## 수치 근거 (게시 전 확인 권장)

- 표면 압축 응력 최대 약 700MPa, 균열 전파 속도 약 1.45–1.9km/s — Chaudhri 등 루퍼트의 눈물 실험 연구에서 보고된 값
- 시속 5,000km 이상 = 1.45km/s 환산값
