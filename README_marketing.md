# 살까말까 — 마케팅 자동화 모듈

기존 `salkka-pipeline/` 레포에 이 파일들을 추가하면 뉴스레터 발송 후
마케팅 에셋이 자동으로 생성됩니다.

## 추가되는 파일

```
salkka-pipeline/
├── marketing/
│   ├── card_generator.py       인스타그램 카드뉴스 HTML (3장)
│   ├── archive_generator.py    SEO 아카이브 웹페이지
│   └── blog_post_generator.py  네이버 블로그/카페/블라인드 게시글 초안
│
└── .github/workflows/
    └── marketing.yml           마케팅 자동화 워크플로우
```

## 세팅 방법 (5분)

```bash
# 1. 파일 복사
cp -r marketing/ /path/to/salkka-pipeline/
cp .github/workflows/marketing.yml /path/to/salkka-pipeline/.github/workflows/

# 2. 커밋
cd /path/to/salkka-pipeline
git add marketing/ .github/workflows/marketing.yml
git commit -m "feat: 마케팅 자동화 모듈 추가"
git push
```

## 자동 실행 흐름

```
매주 월요일 05:00 KST
  └── weekly.yml (뉴스레터 발송) 완료
        └── marketing.yml 자동 트리거
              ├── 인스타그램 카드뉴스 HTML 생성
              ├── SEO 아카이브 페이지 생성
              ├── 블로그/카페/블라인드 게시글 초안 생성
              └── GitHub Pages 자동 배포
```

## 수동 작업 (주 5분)

1. **GitHub Actions → Artifacts** 에서 `marketing-assets` 다운로드
2. `data/cards/card_volNNN.html` → 브라우저 열기 → 각 카드 스크린샷 → 인스타그램
3. `data/posts/naver_blog_volNNN.md` → 네이버 블로그 복붙
4. `data/posts/cafe_post_volNNN.txt` → 부동산 카페 복붙

## 로컬 테스트

```bash
# 테스트용 더미 데이터 생성
python -c "
import json
json.dump({'avg_price': 80000, 'trade_count': 12, 'summary_text': '이번 주 마포구 시장은 안정적인 흐름을 보였습니다.'}, open('data/trades_summary.json','w'), ensure_ascii=False)
json.dump({'신호': '관망 유지', '근거': '거래량이 평년 수준이며 특이 이슈가 없습니다.', '힌트': '급매 물건 위주로 탐색하세요.'}, open('data/timing_result.json','w'), ensure_ascii=False)
json.dump([{'complex_name': '마포래미안푸르지오', 'price': 90000, 'area': 84, 'floor': 10, 'build_year': 2014}], open('data/notable_trades.json','w'), ensure_ascii=False)
"

# 카드뉴스 생성 테스트
python marketing/card_generator.py --vol 1 --region 마포구

# 아카이브 페이지 생성 테스트
python marketing/archive_generator.py --vol 1 --region 마포구

# 게시글 초안 생성 테스트
python marketing/blog_post_generator.py --vol 1 --region 마포구

# 결과 확인
open data/cards/card_vol001.html
```
