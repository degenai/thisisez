import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "how-to-see-comments-on-youtube-ads.html"
JPEG_SAFE_HEADER_MARKERS = {0xE0, 0xDB, 0xC0, 0xC4, 0xDA}
JPEG_FORBIDDEN_SIGNATURES = (
    b"Exif",
    b"http://ns.adobe.com/xap",
    b"ICC_PROFILE",
    b"Photoshop 3.0",
)


def jpeg_header_markers(path):
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise ValueError(f"{path} is not a JPEG")

    markers = []
    position = 2
    while position < len(data):
        while position < len(data) and data[position] == 0xFF:
            position += 1
        marker = data[position]
        position += 1
        markers.append(marker)

        if marker == 0xDA:
            break
        if marker == 0xD9:
            break
        if marker in range(0xD0, 0xD8) or marker == 0x01:
            continue

        segment_length = int.from_bytes(data[position:position + 2], "big")
        if segment_length < 2:
            raise ValueError(f"{path} has an invalid JPEG segment")
        position += segment_length

    return data, set(markers)


class TestYoutubeAdCommentsPage(unittest.TestCase):
    def test_page_has_public_metadata_and_recovery_contract(self):
        html = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '<link rel="canonical" href="https://www.thisisez.com/how-to-see-comments-on-youtube-ads.html">',
            html,
        )
        self.assertIn("<h1>How to see comments on a YouTube ad</h1>", html)
        self.assertIn("Share", html)
        self.assertIn("source video", html.lower())
        self.assertIn("may not work", html.lower())
        self.assertIn("comments are disabled", html.lower())
        self.assertNotIn("noindex", html.lower())

    def test_page_uses_only_public_safe_evidence(self):
        html = PAGE.read_text(encoding="utf-8")
        evidence = [
            ROOT / "assets/youtube-ad-comments/ad-player-share.jpg",
            ROOT / "assets/youtube-ad-comments/source-comments-redacted.jpg",
        ]
        evidence_root = ROOT / "assets/youtube-ad-comments"
        actual_evidence = {path for path in evidence_root.rglob("*") if path.is_file()}
        self.assertEqual(actual_evidence, set(evidence))

        for image in evidence:
            self.assertGreater(image.stat().st_size, 20_000, image)
            self.assertIn(image.relative_to(ROOT).as_posix(), html)
            data, markers = jpeg_header_markers(image)
            self.assertLessEqual(markers, JPEG_SAFE_HEADER_MARKERS, image)
            for signature in JPEG_FORBIDDEN_SIGNATURES:
                self.assertNotIn(signature, data, image)

        self.assertIn("306 comments", html.lower())
        self.assertIn("handles and avatars are redacted", html.lower())
        self.assertNotIn("youtube-ad-source-recovery", html.lower())

        public_text_artifacts = (
            PAGE,
            ROOT / "field-guide.css",
            ROOT / "index.html",
            ROOT / "sitemap.xml",
        )
        for artifact in public_text_artifacts:
            text = artifact.read_text(encoding="utf-8")
            self.assertNotIn("file://", text.lower(), artifact)
            self.assertNotRegex(
                text,
                r"(?i)[a-z]:[\\/](?:users|documents|desktop)[\\/]",
                artifact,
            )

    def test_page_is_linked_from_homepage_and_sitemap(self):
        href = "how-to-see-comments-on-youtube-ads.html"
        url = f"https://www.thisisez.com/{href}"
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        sitemap = ElementTree.parse(ROOT / "sitemap.xml")
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = {
            node.text for node in sitemap.findall("sm:url/sm:loc", namespace)
        }

        self.assertIn(f'href="{href}"', homepage)
        self.assertIn("YouTube ad comments", homepage)
        self.assertIn(url, locations)

    def test_page_has_structured_howto_and_grounded_desktop_fallback(self):
        html = PAGE.read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            html,
            flags=re.DOTALL,
        )

        self.assertIsNotNone(match)
        schema = json.loads(match.group(1))
        self.assertEqual(schema["@type"], "HowTo")
        self.assertEqual(schema["name"], "How to see comments on a YouTube ad")
        self.assertEqual(len(schema["step"]), 4)
        self.assertIn("Copy debug info", html)
        self.assertIn("ad_debug_videoId", html)
        self.assertIn(
            "https://support.google.com/youtube/answer/157177",
            html,
        )
        self.assertIn(
            "https://webapps.stackexchange.com/questions/113412/",
            html,
        )


if __name__ == "__main__":
    unittest.main()
