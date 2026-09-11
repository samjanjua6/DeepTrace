"""
Unit tests for Image Metadata Forensics and Credential Verification.
NIST SP 800-86 Container Metadata Forensics.
"""
import unittest
import re
from app.features.pipeline.tasks.credential_verifier import extract_credential_urls, verify_coursera_credential
from app.features.pipeline.tasks.stage_2_pdf_structure import IMAGE_TAMPER_SOFTWARE_PATTERNS


class TestImageMetadataForensics(unittest.TestCase):
    def test_photopea_software_pattern_detection(self):
        """Test Photopea signature in EXIF Software tag."""
        meta = 'Photopea Editor (www.photopea.com)'
        matched = any(re.search(p, meta, re.I) for p, _ in IMAGE_TAMPER_SOFTWARE_PATTERNS)
        self.assertTrue(matched)

    def test_photoshop_software_pattern_detection(self):
        """Test Adobe Photoshop signature in container metadata."""
        meta = 'Adobe Photoshop 2024 (Windows)'
        matched = any(re.search(p, meta, re.I) for p, _ in IMAGE_TAMPER_SOFTWARE_PATTERNS)
        self.assertTrue(matched)

    def test_credential_extraction_ocr_noise_resilience(self):
        """Test OCR noise resilience when parsing verification URLs."""
        noisy_text = 'Verify at:\nhttpsw//coursera.org/verify/PDC4A6ZTLUYH\nAuthorized by Anthropic'
        urls = extract_credential_urls(noisy_text)
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0]['provider'], 'Coursera')
        self.assertEqual(urls[0]['code'], 'PDC4A6ZTLUYH')

    def test_fake_coursera_credential_registry_check(self):
        """Test that fabricated Coursera credentials return null/invalid record."""
        is_valid, reason, _ = verify_coursera_credential('P852GMRZLETH')
        self.assertFalse(is_valid)
        self.assertIn('does not exist', reason)


if __name__ == '__main__':
    unittest.main()
