#!/usr/bin/env python3
"""Fetch exact recipe matches and photo provenance; never publish unreviewed data.

Run after Internet access is configured:
  python3 scripts/research_cocktails.py --output /tmp/cocktail-research

Only exact normalized names or explicit aliases match. Photos are downloaded only
when the source explicitly confirms Creative Commons status. The resulting report
still requires license/attribution checks and editorial review before publication.
"""
import argparse
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    'aperol-spritz': ['Aperol Spritz', 'Spritz'],
    'mai-tai': ['Mai Tai', 'Mai-Tai'],
    'hemingway-daiquiri': ['Hemingway Daiquiri', 'Hemingway Special'],
    'godfather': ['Godfather', 'God Father'],
    'godmother': ['Godmother', 'God Mother'],
    'porn-star-martini': ['Porn Star Martini', 'Pornstar Martini'],
    'bee-s-knees': ["Bee's Knees", 'Bees Knees'],
    'corpse-reviver-no-2': ['Corpse Reviver No. 2', 'Corpse Reviver #2'],
}


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower())


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'DrunkenGuideCatalogResearch/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(), response.headers.get_content_type()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100:
        parser.error('--limit must be 1..100')
    plan = json.loads((ROOT / 'content/cocktails-plan.json').read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    report = []
    for item in plan['cocktails'][:args.limit]:
        row = {'id': item['id'], 'name': item['name'], 'status': 'not_found'}
        try:
            candidates = ALIASES.get(item['id'], [item['name']])
            match = None
            used_url = None
            for name in candidates:
                url = 'https://www.thecocktaildb.com/api/json/v1/1/search.php?' + urllib.parse.urlencode({'s': name})
                payload, mime = get(url)
                data = json.loads(payload)
                accepted = {normalized(n) for n in candidates}
                matches = [r for r in (data.get('drinks') or []) if normalized(r.get('strDrink', '')) in accepted and r.get('strAlcoholic') == 'Alcoholic']
                if len(matches) == 1:
                    match, used_url = matches[0], url
                    break
                time.sleep(.25)
            if match:
                photo = match.get('strDrinkThumb')
                row.update(status='needs_editorial_review', source_url=used_url, source_record=match,
                           photo_url=photo, attribution=match.get('strImageAttribution'),
                           image_source=match.get('strImageSource'),
                           creative_commons_confirmed=match.get('strCreativeCommonsConfirmed'),
                           license_status='needs_license_and_attribution_review')
                if photo and match.get('strCreativeCommonsConfirmed') == 'Yes':
                    parsed = urllib.parse.urlsplit(photo)
                    if parsed.scheme != 'https' or parsed.hostname not in {'www.thecocktaildb.com', 'thecocktaildb.com'}:
                        row['photo_download_status'] = 'unexpected_host_not_downloaded'
                    else:
                        image, mime = get(photo)
                        if mime in {'image/jpeg', 'image/png', 'image/webp'}:
                            suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}[mime]
                            target = args.output / (item['id'] + suffix)
                            target.write_bytes(image)
                            row['local_photo'] = target.name
                else:
                    row['photo_download_status'] = 'rights_not_confirmed_not_downloaded'
        except Exception as error:
            row['status'] = 'blocked_or_failed'
            row['error'] = str(error)
            if isinstance(error, urllib.error.HTTPError) and error.code in {401, 403}:
                report.append(row)
                (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
                raise SystemExit(f"Access denied for {item['name']}; stopping instead of retrying all 100.") from error
        report.append(row)
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(item['name'], row['status'])
        time.sleep(.3)
    print(f'Report: {args.output / "report.json"}. Review before publishing.')


if __name__ == '__main__':
    main()
