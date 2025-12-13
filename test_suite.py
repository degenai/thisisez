import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
from PIL import Image
import harvester
import consolidator

# janitor exits at import time if no API key - conditionally import
try:
    import janitor
    JANITOR_AVAILABLE = True
except SystemExit:
    janitor = None
    JANITOR_AVAILABLE = False


class TestModelConfiguration(unittest.TestCase):
    """Tests to ensure correct Gemini model names are configured."""
    
    def test_harvester_uses_flash_model(self):
        """Harvester should use gemini-2.5-flash for thread analysis."""
        self.assertEqual(harvester.MODEL_FLASH, 'gemini-2.5-flash')
    
    def test_consolidator_uses_flash_for_bulk(self):
        """Consolidator should use gemini-2.5-flash for bulk operations."""
        self.assertEqual(consolidator.MODEL_FLASH, 'gemini-2.5-flash')
    
    def test_consolidator_uses_pro_for_metanarrative(self):
        """Consolidator should use gemini-3-pro-preview for grand metanarrative."""
        self.assertEqual(consolidator.MODEL_PRO, 'gemini-3-pro-preview')
    
    def test_models_are_different(self):
        """Flash and Pro models should be different (Pro is for premium tasks)."""
        self.assertNotEqual(consolidator.MODEL_FLASH, consolidator.MODEL_PRO)
    
    @patch('consolidator.model_pro')
    @patch('consolidator.model')
    def test_grand_metanarrative_uses_pro_model(self, mock_flash, mock_pro):
        """Grand metanarrative generation should prefer Pro model over Flash."""
        mock_pro.generate_content.return_value.text = "Test metanarrative"
        
        # Create test thread data
        threads = [
            {'gestalt_summary': 'Test summary 1', 'radar': {'GREED': 50, 'FEAR': 30, 'SCHIZO': 20}},
            {'gestalt_summary': 'Test summary 2', 'radar': {'GREED': 60, 'FEAR': 40, 'SCHIZO': 10}}
        ]
        
        result = consolidator.generate_grand_metanarrative(threads)
        
        # Pro model should be called, not Flash
        mock_pro.generate_content.assert_called_once()
        mock_flash.generate_content.assert_not_called()
        self.assertEqual(result['narrative'], "Test metanarrative")

class TestHarvester(unittest.TestCase):

    @patch('harvester.requests.get')
    def test_get_catalog_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "threads": [
                    {"no": 1, "sub": "Thread 1", "com": "Comment 1", "replies": 10},
                    {"no": 2, "sub": "Thread 2", "com": "Comment 2", "replies": 5}
                ]
            }
        ]
        mock_get.return_value = mock_response

        catalog = harvester.get_catalog("biz")
        self.assertEqual(len(catalog), 1)
        self.assertEqual(catalog[0]['no'], 1)

    @patch('harvester.requests.get')
    def test_get_catalog_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        catalog = harvester.get_catalog("biz")
        self.assertEqual(catalog, [])

    @patch('harvester.genai.GenerativeModel')
    @patch('harvester.requests.get')
    def test_distill_thread_success(self, mock_get, mock_model_cls):
        mock_thread_response = MagicMock()
        mock_thread_response.status_code = 200
        mock_thread_response.json.return_value = {
            "posts": [
                {"no": 1, "com": "OP Post"},
                {"no": 2, "com": "Reply 1"}
            ]
        }
        mock_get.return_value = mock_thread_response

        mock_model_instance = mock_model_cls.return_value
        expected_json = {
            "gestalt_summary": "Test Summary",
            "radar": {"GREED": 50, "FEAR": 50, "IQ": 50, "SCHIZO": 50, "SHILL": 50},
            "keywords": ["TEST"],
            "assets": []
        }
        mock_model_instance.generate_content.return_value.text = json.dumps(expected_json)

        thread_data = {"no": 123, "sub": "Test Thread", "replies": 50}
        result, error = harvester.distill_thread(thread_data, mock_model_instance)

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], "thread_123")
        self.assertEqual(result['gestalt_summary'], "Test Summary")

    @patch('harvester.open', new_callable=mock_open)
    @patch('harvester.datetime')
    def test_export_gestalt_creates_manifest(self, mock_datetime, mock_file):
        mock_datetime.now.return_value.strftime.return_value = "20230101_120000"
        test_data = [{"id": "test"}]
        harvester.export_gestalt(test_data)
        
        expected_filename = "gestalt_export_20230101_120000.json"
        mock_file.assert_any_call(expected_filename, 'w')
        mock_file.assert_any_call("latest_manifest.json", 'w')

    def test_distill_thread_no_model_returns_tuple(self):
        """Ensure distill_thread returns a tuple even when no model is available."""
        thread_data = {"no": 999, "sub": "Test Thread", "replies": 10}
        
        # Call with model_instance=None (simulates no API key scenario)
        result = harvester.distill_thread(thread_data, model_instance=None)
        
        # Must return a tuple of (result, error_code)
        self.assertIsInstance(result, tuple, "distill_thread must return a tuple")
        self.assertEqual(len(result), 2, "distill_thread must return exactly 2 values")
        
        gestalt, error_code = result
        self.assertIsNotNone(gestalt, "gestalt should not be None for mock data")
        self.assertEqual(gestalt['id'], "thread_999")
        self.assertIn(error_code, [None, "NO_MODEL", "MOCK_USED"], "error_code should be valid")

class TestConsolidator(unittest.TestCase):
    @patch('consolidator.os.path.exists')
    def test_load_data_from_manifest_legacy_format(self, mock_exists):
        """Test loading legacy format (array) and converting to unified."""
        mock_exists.return_value = True
        manifest_content = '{"latest": "timestamped_file.json"}'
        # Legacy format: just an array of threads
        data_content = '[{"id": "1", "assets": [{"name": "BTC"}]}]'
        
        def side_effect(filename, mode='r', *args, **kwargs):
            if filename == 'latest_manifest.json':
                return mock_open(read_data=manifest_content).return_value
            elif filename == 'timestamped_file.json':
                return mock_open(read_data=data_content).return_value
            elif filename == 'canonical_assets.json':
                return mock_open(read_data='{}').return_value
            else:
                raise FileNotFoundError(filename)
                
        with patch('builtins.open', side_effect=side_effect):
            threads, unified_data, filename = consolidator.load_data()
            self.assertEqual(filename, "timestamped_file.json")
            self.assertEqual(len(threads), 1)
            self.assertIn("threads", unified_data)
            self.assertEqual(unified_data["dashboard"], None)  # Not yet aggregated
    
    @patch('consolidator.os.path.exists')
    def test_load_data_from_manifest_unified_format(self, mock_exists):
        """Test loading new unified format (object with threads/dashboard)."""
        mock_exists.return_value = True
        manifest_content = '{"latest": "timestamped_file.json"}'
        # New unified format
        unified_content = json.dumps({
            "threads": [{"id": "1", "assets": [{"name": "BTC"}]}],
            "dashboard": {"metadata": {"flux_score": 50}, "assets": []}
        })
        
        def side_effect(filename, mode='r', *args, **kwargs):
            if filename == 'latest_manifest.json':
                return mock_open(read_data=manifest_content).return_value
            elif filename == 'timestamped_file.json':
                return mock_open(read_data=unified_content).return_value
            elif filename == 'canonical_assets.json':
                return mock_open(read_data='{}').return_value
            else:
                raise FileNotFoundError(filename)
                
        with patch('builtins.open', side_effect=side_effect):
            threads, unified_data, filename = consolidator.load_data()
            self.assertEqual(filename, "timestamped_file.json")
            self.assertEqual(len(threads), 1)
            self.assertIn("threads", unified_data)
            self.assertIn("dashboard", unified_data)
            self.assertIsNotNone(unified_data["dashboard"])

    @patch('consolidator.os.path.exists')
    def test_clean_name_with_aliases(self, mock_exists):
        # Mock canonical assets loading
        mock_exists.return_value = True
        aliases = {"LINK": "CHAINLINK", "WIF": "DOGWIFHAT"}
        
        with patch('builtins.open', mock_open(read_data=json.dumps(aliases))):
            # We need to ensure clean_name reloads or we mock the internal load
            # Since clean_name loads every time (inefficient but safe for now), mocking open works.
            
            self.assertEqual(consolidator.clean_name("LINK"), "CHAINLINK")
            self.assertEqual(consolidator.clean_name("WIF"), "DOGWIFHAT")
            self.assertEqual(consolidator.clean_name("BTC"), "BTC") # No alias

@unittest.skipUnless(JANITOR_AVAILABLE, "janitor module requires API key")
class TestJanitor(unittest.TestCase):
    
    def test_extract_unique_assets_legacy_format(self):
        """Test extracting assets from legacy array format."""
        file_content = json.dumps([
            {"assets": [{"name": "BTC"}, {"name": "ETH"}]},
            {"assets": [{"name": "BTC"}, {"name": "SOL"}]}
        ])
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            assets = janitor.extract_unique_assets(["dummy_file.json"])
            self.assertIn("BTC", assets)
            self.assertIn("ETH", assets)
            self.assertIn("SOL", assets)
            self.assertEqual(len(assets), 3)
    
    def test_extract_unique_assets_unified_format(self):
        """Test extracting assets from new unified format."""
        file_content = json.dumps({
            "threads": [
                {"assets": [{"name": "BTC"}, {"name": "ETH"}]},
                {"assets": [{"name": "BTC"}, {"name": "LINK"}]}
            ],
            "dashboard": None
        })
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            assets = janitor.extract_unique_assets(["dummy_file.json"])
            self.assertIn("BTC", assets)
            self.assertIn("ETH", assets)
            self.assertIn("LINK", assets)
            self.assertEqual(len(assets), 3)

    @patch('janitor.genai.GenerativeModel')
    def test_identify_aliases(self, mock_model_cls):
        mock_model = mock_model_cls.return_value
        mock_response = MagicMock()
        mock_response.text = '[{"alias": "MESSY_COIN", "canonical": "CLEAN_COIN"}]'
        mock_model.generate_content.return_value = mock_response
        
        new_assets = ["MESSY_COIN", "CLEAN_COIN"]
        canonical_map = {}
        
        proposals = janitor.identify_aliases(new_assets, canonical_map)
        
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['alias'], "MESSY_COIN")
        self.assertEqual(proposals[0]['canonical'], "CLEAN_COIN")

class TestImageAndQuote(unittest.TestCase):
    def setUp(self):
        self.mock_thread = {
            'no': 999999,
            'sub': 'Test Thread with Image',
            'com': 'This is the OP post.',
            'tim': '1234567890',
            'ext': '.png',
            'replies': 10
        }
        
        # Mock Gemini Response
        self.mock_response_json = {
            "subject": "Test Thread with Image",
            "is_generated_subject": False,
            "gestalt_summary": "A test thread.",
            "radar": { "GREED": 50, "FEAR": 10, "SCHIZO": 20, "IQ": 80, "SHILL": 5, "CHUCKLE_FACTOR": 90 },
            "keywords": ["TEST", "IMAGE"],
            "top_quote": "This is the best quote ever.",
            "image_analysis": "A chart showing a bullish trend.",
            "assets": [{"name": "TESTCOIN", "narrative": "Moon soon.", "sentiment": "BULLISH"}]
        }
        
        self.mock_model = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.text = json.dumps(self.mock_response_json)
        self.mock_model.generate_content.return_value = self.mock_response

    @patch('harvester.requests.get')
    def test_distill_thread_with_image_and_quote(self, mock_get):
        # Mock Image Fetch
        # Ensure testimg.png exists or create a dummy one for the test if needed, 
        # but the user said they provided it.
        if not os.path.exists("testimg.png"):
             # Fallback if file missing in CI/CD, though user said it's there
             img_bytes = b'fake_image_data'
        else:
            with open("testimg.png", "rb") as f:
                img_bytes = f.read()
            
        mock_img_response = MagicMock()
        mock_img_response.status_code = 200
        mock_img_response.content = img_bytes
        
        # Mock Thread Replies Fetch
        mock_thread_response = MagicMock()
        mock_thread_response.status_code = 200
        mock_thread_response.json.return_value = {'posts': [{'no': 999999, 'com': 'OP'}, {'no': 1000000, 'com': 'Reply 1'}]}
        
        # Configure side_effect for requests.get
        def side_effect(url, stream=False):
            if "i.4cdn.org" in url:
                return mock_img_response
            if "api.4cdn.org" in url or ".json" in url:
                return mock_thread_response
            return MagicMock(status_code=404)
            
        mock_get.side_effect = side_effect

        # Run Distillation
        result, error = harvester.distill_thread(self.mock_thread, self.mock_model)
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['top_quote'], "This is the best quote ever.")
        self.assertEqual(result['image_analysis'], "A chart showing a bullish trend.")
        self.assertEqual(result['radar']['CHUCKLE_FACTOR'], 90)
        
        # Verify Model Call included Image
        call_args = self.mock_model.generate_content.call_args
        content_payload = call_args[0][0]
        self.assertTrue(any(isinstance(x, Image.Image) for x in content_payload), "Image object should be passed to model")

if __name__ == '__main__':
    unittest.main()
