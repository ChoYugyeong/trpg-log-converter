# TRPG 로그 변환기 Pro

코코포리아(Ccfolia) / Roll20 채팅 로그를 EPUB / DOCX 전자책으로 변환하는 도구입니다.

![screenshot](screenshot.png)

## 주요 기능

- **코코포리아 / Roll20 로그 지원** - HTML 파일 또는 Roll20 URL에서 직접 변환
- **EPUB / DOCX 출력** - 전자책 리더 또는 워드에서 바로 열기
- **자동 장면 분할** - 장면 마커(■, 씬 등)를 인식하여 챕터 자동 생성
- **나레이션 스타일링** - GM/나레이터 텍스트를 소설처럼 표현
- **다이스 / 이펙트 표시** - 주사위 결과와 스킬 효과 포함

## 다운로드

### macOS
1. [TRPG_Converter_Pro_macOS.zip](releases) 다운로드
2. 압축 해제
3. `TRPG_Converter_Pro.app` 실행

> ⚠️ "확인되지 않은 개발자" 경고가 뜨면: 우클릭 → 열기 → 열기 클릭

### Windows
1. [TRPG_Converter_Pro_Windows.zip](releases) 다운로드
2. 압축 해제
3. `TRPG_Converter_Pro.exe` 실행

## 사용법

### 1. 파일 변환 (기본)

1. **파일 선택** 버튼 클릭 또는 드래그앤드롭
2. 제목/저자 입력
3. 출력 형식 선택 (EPUB, DOCX, 또는 둘 다)
4. **변환 시작** 클릭

### 2. Roll20 로그 가져오기

Roll20 채팅 아카이브를 간편하게 가져올 수 있습니다.

1. **브라우저에서 Roll20 채팅 아카이브 페이지 열기**
   ```
   https://app.roll20.net/campaigns/chatarchive/12345678
   ```

2. **HTML 파일로 저장**
   - `Ctrl+S` 눌러서 저장
   - "웹페이지, HTML만" 선택 (다운로드 폴더에 저장됨)

3. **앱에서 가져오기**
   - "저장한 Roll20 HTML 가져오기" 버튼 클릭
   - 다운로드 폴더가 자동으로 열림
   - 저장한 파일 선택

### 3. input 폴더 사용

1. `input` 폴더에 HTML 파일 넣기
2. **input 폴더** 버튼 클릭
3. 자동으로 모든 파일 추가됨

## 설정

우측 상단 **설정** 버튼에서 세부 옵션 조정:

| 설정 | 설명 |
|------|------|
| GM 이름 | 나레이션으로 처리할 이름 (쉼표 구분) |
| 장면 패턴 | 장면 구분 마커 (예: ■, 씬, Scene) |
| 분할 모드 | scene(마커), count(항목수), none |
| 나레이션 접두사 | 나레이션 앞에 붙는 기호 |
| 출력 폴더 | 변환된 파일 저장 위치 |

## 폴더 구조

```
TRPG_Converter_Pro/
├── input/          # 변환할 HTML 파일
├── export/         # 생성된 EPUB/DOCX 파일
├── images/         # 삽화 이미지 (선택)
├── fonts/          # 커스텀 폰트 (선택)
└── config.yaml     # 고급 설정 (선택)
```

## 직접 빌드하기

### 요구사항
- Python 3.9+
- pip

### 설치
```bash
cd TRPG_Converter_Pro
pip install -r requirements.txt
```

### 실행
```bash
python main.py
```

### 배포용 빌드
```bash
python build.py
```
→ `dist/` 폴더에 실행 파일 생성

## 웹 배포

GitHub, Google Drive, Dropbox 등에 올릴 파일:

1. **macOS**: `dist/TRPG_Converter_Pro.app` → zip 압축
2. **Windows**: `dist/TRPG_Converter_Pro/` 폴더 전체 → zip 압축

## 문제 해결

### "확인되지 않은 개발자" (macOS)
```bash
xattr -cr /path/to/TRPG_Converter_Pro.app
```

### 의존성 오류
```bash
pip install customtkinter ebooklib beautifulsoup4 lxml python-docx pyyaml
```

### 한글 깨짐
- EPUB: 전자책 리더 폰트 설정 확인
- DOCX: "맑은 고딕" 폰트 필요

## 라이선스

MIT License

## 크레딧

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [ebooklib](https://github.com/aerkalov/ebooklib)
- [python-docx](https://github.com/python-openxml/python-docx)
