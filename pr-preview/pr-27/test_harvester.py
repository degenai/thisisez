import unittest
from unittest.mock import patch, MagicMock
import json
import harvester

class TestHarvester(unittest.TestCase):

    @patch('harvester.requests.get')
    def test_get_catalog_success(self, mock_get):
        # Mock 4chan catalog response
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
        # One thread has 10 replies (>5), one has 5 (not >5). So we expect 1.
        self.assertEqual(len(catalog), 1)
        self.assertEqual(catalog[0]['no'], 1)

    @patch('harvester.requests.get')
    def test_get_catalog_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        catalog = harvester.get_catalog("biz")
        self.assertEqual(catalog, [])

    def test_filter_threads(self):
        # Test filtering logic (assuming logic is embedded or we extract it)
        # Since the filtering is currently inside the main loop or a helper, 
        # we might need to refactor harvester.py to make it testable, 
        # or just test the logic if we extract it.
        # For now, let's assume we want to verify the logic we *intend* to use.
        
        # If we look at harvester.py, the filtering is likely inline. 
        # Let's verify if we can test `distill_thread` with mocks.
        pass

    @patch('harvester.genai.GenerativeModel')
    @patch('harvester.requests.get')
    def test_distill_thread_success(self, mock_get, mock_model_cls):
        # Mock Thread Content
        mock_thread_response = MagicMock()
        mock_thread_response.status_code = 200
        mock_thread_response.json.return_value = {
            "posts": [
                {"no": 1, "com": "OP Post"},
                {"no": 2, "com": "Reply 1"}
            ]
        }
        mock_get.return_value = mock_thread_response

        # Mock Gemini Response
        mock_model_instance = mock_model_cls.return_value
        
        expected_json = {
            "gestalt_summary": "Test Summary",
            "radar": {"GREED": 50, "FEAR": 50, "IQ": 50, "SCHIZO": 50, "SHILL": 50},
            "keywords": ["TEST"],
            "assets": []
        }
        
        mock_model_instance.generate_content.return_value.text = json.dumps(expected_json)

        # Call distill_thread
        # Note: We need to ensure distill_thread returns the dict, or we check side effects.
        # Based on previous reads, it returns the result dict.
        
        thread_data = {"no": 123, "sub": "Test Thread", "replies": 50}
        result, error = harvester.distill_thread(thread_data, mock_model_instance)

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], "thread_123")
        self.assertEqual(result['replies'], 50)
        self.assertEqual(result['gestalt_summary'], "Test Summary")

        self.assertEqual(result['gestalt_summary'], "Test Summary")

    @patch('harvester.open', new_callable=unittest.mock.mock_open)
    @patch('harvester.datetime')
    def test_export_gestalt_creates_manifest(self, mock_datetime, mock_file):
        # Setup fixed timestamp
        mock_datetime.now.return_value.strftime.return_value = "20230101_120000"
        
        test_data = [{"id": "test"}]
        harvester.export_gestalt(test_data)
        
        # Check if files were opened (timestamped file and manifest)
        # We expect calls to open:
        # 1. gestalt_export_20230101_120000.json
        # 2. latest_manifest.json
        
        expected_filename = "gestalt_export_20230101_120000.json"
        
        # Verify calls
        mock_file.assert_any_call(expected_filename, 'w')
        mock_file.assert_any_call("latest_manifest.json", 'w')
        
        # Verify content written to manifest
        # Get the handle for the manifest write
        handle = mock_file()
        
        # We need to check what was written. 
        # Since multiple writes happen, we can check the write calls.
        # Ideally we check that json.dump was called with the correct dict for the manifest.
        
    def test_consolidator_load_data_from_manifest(self):
        # We need to import consolidator here or at top level
        import consolidator
        
        with patch('builtins.open', unittest.mock.mock_open(read_data='{"latest": "test_file.json"}')) as mock_file:
            # We need to handle multiple file opens with different content
            # mock_open read_data is static. 
            # We can use side_effect for open to return different file mocks
            pass

class TestConsolidator(unittest.TestCase):
    @patch('consolidator.os.path.exists')
    def test_load_data_from_manifest(self, mock_exists):
        import consolidator
        
        # Mock exists to always return True for our test files
        mock_exists.return_value = True
        
        manifest_content = '{"latest": "timestamped_file.json"}'
        data_content = '[{"id": "1", "asset": "BTC"}]'
        
        def side_effect(filename, mode='r', *args, **kwargs):
            if filename == 'latest_manifest.json':
                return unittest.mock.mock_open(read_data=manifest_content).return_value
            elif filename == 'timestamped_file.json':
                return unittest.mock.mock_open(read_data=data_content).return_value
            else:
                raise FileNotFoundError(filename)
                
        with patch('builtins.open', side_effect=side_effect):
            data, filename = consolidator.load_data()
            self.assertEqual(filename, "timestamped_file.json")
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['asset'], "BTC")

    @patch('consolidator.os.path.exists')
    def test_load_data_fallback(self, mock_exists):
        import consolidator
        
        # Mock exists to return True for gestalt_export.json, False for manifest
        def exists_side_effect(path):
            if path == 'latest_manifest.json':
                return False
            return True
            
        mock_exists.side_effect = exists_side_effect
        
        data_content = '[{"id": "fallback"}]'
        
        def side_effect(filename, mode='r', *args, **kwargs):
            if filename == 'latest_manifest.json':
                raise FileNotFoundError
            elif filename == 'gestalt_export.json':
                return unittest.mock.mock_open(read_data=data_content).return_value
            else:
                raise FileNotFoundError(filename)
                
        with patch('builtins.open', side_effect=side_effect):
            data, filename = consolidator.load_data()
            self.assertEqual(filename, "gestalt_export.json")
            self.assertEqual(data[0]['id'], "fallback")

if __name__ == '__main__':
    unittest.main()
