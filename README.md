# 관심종목 대시보드 PWA

4개 종목의 최신 종가, 2026-05-22 종가 대비 수익률, 관련 뉴스를 보여주는 GitHub Pages용 웹앱입니다.
모바일에서 홈 화면에 추가하면 앱처럼 사용할 수 있습니다.

## 포함 종목

- KODEX 200선물인버스2X (252670), 기준가 102원
- 성광벤드 (014620), 기준가 36,250원
- 신테카바이오 (226330), 기준가 2,505원
- 화신 (010690), 기준가 12,730원

## 사용 방법

1. GitHub에서 새 저장소를 만듭니다. 예: `stock-dashboard`
2. 이 폴더 안의 모든 파일과 폴더를 저장소에 업로드합니다.
   - `.github` 폴더도 반드시 업로드해야 합니다.
3. 저장소의 `Settings` → `Pages`로 이동합니다.
4. `Source`를 `GitHub Actions`로 설정합니다.
5. 저장소의 `Actions` → `Daily stock dashboard update` → `Run workflow`를 눌러 첫 배포를 실행합니다.
6. 완료 후 `Settings` → `Pages`에서 사이트 주소를 확인합니다.

주소 예시:

```text
https://깃허브아이디.github.io/stock-dashboard/
```

## 모바일 앱처럼 설치

- 아이폰: Safari로 사이트 접속 → 공유 버튼 → 홈 화면에 추가
- 안드로이드: Chrome으로 사이트 접속 → 메뉴 → 홈 화면에 추가 또는 앱 설치

## 자동 업데이트 시간

매일 한국시간 20:00에 자동 업데이트됩니다.
GitHub Actions는 UTC 기준이므로 워크플로에는 `0 11 * * *`로 설정되어 있습니다.

## 뉴스 표시

네이버 뉴스 API 키가 없으면 네이버 뉴스 검색 링크가 표시됩니다.
뉴스 제목을 자동 표시하려면 저장소에서 아래 Secrets를 등록하세요.

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

## 종목이나 기준가 수정

`config.json` 파일을 수정하면 됩니다.
