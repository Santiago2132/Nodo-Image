#!/usr/bin/env python3
import os
import time
import base64
import requests
import threading
import statistics
import json
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Generator
import xml.etree.ElementTree as ET

class UltraStressTest:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.image_data = self._load_image()
        self.transformations = self._get_optimized_transformations()
        self.session = requests.Session()
        self.session.headers.update({'Connection': 'keep-alive'})
        
    def _load_image(self) -> str:
        """Carga imagen optimizada con compresión"""
        image_files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp'))]
        if not image_files:
            # Create test image if none found
            from PIL import Image
            import io
            img = Image.new('RGB', (1024, 768), color='red')
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        with open(image_files[0], 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _get_optimized_transformations(self) -> List[List[Dict]]:
        """Transformaciones optimizadas por complejidad"""
        return {
            'light': [
                {'type': 'resize', 'width': 800, 'height': 600},
                {'type': 'brightness_contrast', 'brightness': 1.2}
            ],
            'medium': [
                {'type': 'resize', 'width': 1200, 'height': 900},
                {'type': 'grayscale'},
                {'type': 'blur', 'blur_type': 'gaussian', 'radius': 2.0},
                {'type': 'brightness_contrast', 'brightness': 1.2, 'contrast': 1.1}
            ],
            'heavy': [
                {'type': 'resize', 'width': 1600, 'height': 1200},
                {'type': 'rotate', 'degrees': 90},
                {'type': 'watermark', 'text': 'STRESS_TEST', 'position': '(50,50)', 'font_size': 30},
                {'type': 'sharpen', 'factor': 1.5},
                {'type': 'autocontrast'}
            ],
            'extreme': [
                {'type': 'resize', 'width': 2048, 'height': 1536},
                {'type': 'blur', 'blur_type': 'gaussian', 'radius': 3.0},
                {'type': 'brightness_contrast', 'brightness': 1.3, 'contrast': 1.2},
                {'type': 'rotate', 'degrees': 180},
                {'type': 'watermark', 'text': 'EXTREME_TEST', 'position': '(100,100)', 'font_size': 40}
            ]
        }
    
    def _create_batch_xml(self, batch_size: int, complexity: str = 'medium') -> str:
        """Crea XML para batch testing masivo"""
        transformations = self.transformations[complexity]
        
        xml_parts = ['<images>']
        
        for i in range(batch_size):
            xml_parts.append(f'  <image id="{i}">')
            xml_parts.append(f'    <data>{self.image_data}</data>')
            
            for trans in transformations:
                xml_line = f'    <transformation type="{trans["type"]}"'
                for key, value in trans.items():
                    if key != 'type':
                        xml_line += f' {key}="{value}"'
                xml_line += '/>'
                xml_parts.append(xml_line)
            
            xml_parts.append('  </image>')
        
        xml_parts.append('</images>')
        return '\n'.join(xml_parts)
    
    def _single_request(self, xml_data: str, endpoint: str = "/process") -> Tuple[float, bool, int]:
        """Request optimizado con métricas detalladas"""
        start_time = time.time()
        response_size = 0
        
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=300,  # 5 minutos para batches grandes
                stream=True
            )
            
            # Stream response to avoid memory issues
            response_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                response_size += len(chunk)
            
            success = response.status_code == 200
            return time.time() - start_time, success, response_size
            
        except Exception as e:
            print(f"Request error: {e}")
            return time.time() - start_time, False, 0
    
    def _get_server_metrics(self) -> Dict:
        """Obtiene métricas del servidor"""
        try:
            response = self.session.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.text)
                metrics = {}
                for child in root:
                    try:
                        value = float(child.text) if child.text.replace('.', '').isdigit() else child.text
                        metrics[child.tag] = value
                    except:
                        metrics[child.tag] = child.text
                return metrics
        except:
            pass
        return {}
    
    def run_batch_test(self, batch_sizes: List[int], complexity: str = 'medium') -> Dict:
        """Test de batches progresivos"""
        results = {}
        
        print(f"\n🚀 BATCH TEST - Complexity: {complexity.upper()}")
        print(f"Transformations: {len(self.transformations[complexity])}")
        
        for batch_size in batch_sizes:
            print(f"\n--- Testing batch size: {batch_size:,} images ---")
            
            # Create batch XML
            xml_data = self._create_batch_xml(batch_size, complexity)
            xml_size = len(xml_data.encode('utf-8')) / (1024 * 1024)  # MB
            print(f"XML size: {xml_size:.2f} MB")
            
            # Get initial server metrics
            initial_metrics = self._get_server_metrics()
            initial_memory = psutil.virtual_memory().percent
            
            # Execute test
            start_time = time.time()
            duration, success, response_size = self._single_request(xml_data)
            total_time = time.time() - start_time
            
            # Get final server metrics
            final_metrics = self._get_server_metrics()
            final_memory = psutil.virtual_memory().percent
            
            # Calculate metrics
            images_per_second = batch_size / duration if duration > 0 and success else 0
            mb_processed = (len(xml_data.encode('utf-8')) + response_size) / (1024 * 1024)
            throughput_mbps = mb_processed / duration if duration > 0 and success else 0
            
            result = {
                'batch_size': batch_size,
                'complexity': complexity,
                'xml_size_mb': xml_size,
                'duration': duration,
                'success': success,
                'response_size_mb': response_size / (1024 * 1024),
                'images_per_second': images_per_second,
                'throughput_mbps': throughput_mbps,
                'memory_usage_change': final_memory - initial_memory,
                'server_metrics': {
                    'initial': initial_metrics,
                    'final': final_metrics
                }
            }
            
            results[batch_size] = result
            
            # Print results
            if success:
                print(f"✅ SUCCESS")
                print(f"   Duration: {duration:.2f}s")
                print(f"   Images/sec: {images_per_second:.2f}")
                print(f"   Throughput: {throughput_mbps:.2f} MB/s")
                print(f"   Memory change: {final_memory - initial_memory:+.1f}%")
                
                if 'cpu_percent' in final_metrics:
                    print(f"   Server CPU: {final_metrics['cpu_percent']:.1f}%")
                if 'memory_percent' in final_metrics:
                    print(f"   Server Memory: {final_metrics['memory_percent']:.1f}%")
            else:
                print(f"❌ FAILED")
                print(f"   Duration: {duration:.2f}s")
            
            # Cool down period for large batches
            if batch_size >= 10000:
                print("   Cooling down...")
                time.sleep(5)
        
        return results
    
    def run_scalability_test(self) -> Dict:
        """Test de escalabilidad completo"""
        test_scenarios = [
            # (batch_sizes, complexity, description)
            ([1, 10, 100], 'extreme', 'Extreme Quality Test'),
            ([100, 500, 1000], 'heavy', 'Heavy Load Test'),
            ([1000, 5000, 10000], 'medium', 'Medium Scale Test'),
            ([10000, 50000, 100000], 'light', 'High Volume Test'),
            ([100000, 500000, 1000000], 'light', 'Ultra Scale Test')
        ]
        
        all_results = {}
        
        for batch_sizes, complexity, description in test_scenarios:
            print(f"\n{'='*80}")
            print(f"SCENARIO: {description}")
            print(f"{'='*80}")
            
            try:
                results = self.run_batch_test(batch_sizes, complexity)
                all_results[description] = results
                
                # Analyze breaking point
                successful_batches = [size for size, result in results.items() if result['success']]
                if successful_batches:
                    max_successful = max(successful_batches)
                    print(f"\n📊 Max successful batch: {max_successful:,} images")
                    
                    if max_successful in results:
                        best = results[max_successful]
                        print(f"    Performance: {best['images_per_second']:.1f} img/s")
                        print(f"    Throughput: {best['throughput_mbps']:.1f} MB/s")
                
            except KeyboardInterrupt:
                print(f"\n⏸️  Test interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Scenario failed: {e}")
                continue
        
        return all_results
    
    def run_concurrent_nodes_test(self, batch_size: int = 1000) -> Dict:
        """Test de múltiples nodos concurrentes"""
        ports = [8001, 8002, 8003, 8004, 8005, 8006]  # All available nodes
        xml_data = self._create_batch_xml(batch_size, 'medium')
        
        print(f"\n🔗 CONCURRENT NODES TEST")
        print(f"Testing {len(ports)} nodes with {batch_size:,} images each")
        
        results = {}
        
        def test_node(port):
            url = f"http://localhost:{port}"
            session = requests.Session()
            
            try:
                # Health check
                health = session.get(f"{url}/health", timeout=5)
                if health.status_code != 200:
                    return port, {'success': False, 'error': 'Node unhealthy'}
                
                # Process test
                start_time = time.time()
                response = session.post(
                    f"{url}/process",
                    data=xml_data.encode('utf-8'),
                    headers={'Content-Type': 'application/xml'},
                    timeout=180
                )
                
                duration = time.time() - start_time
                success = response.status_code == 200
                
                return port, {
                    'success': success,
                    'duration': duration,
                    'images_per_second': batch_size / duration if duration > 0 and success else 0,
                    'node_type': health.json().get('node_type', 'unknown')
                }
                
            except Exception as e:
                return port, {'success': False, 'error': str(e)}
        
        # Test all nodes concurrently
        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = [executor.submit(test_node, port) for port in ports]
            
            for future in as_completed(futures):
                port, result = future.result()
                results[port] = result
                
                if result['success']:
                    print(f"✅ Node {port} ({result.get('node_type', '?')}): "
                          f"{result['duration']:.2f}s, {result['images_per_second']:.1f} img/s")
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"❌ Node {port}: {error}")
        
        # Calculate aggregate performance
        successful_nodes = [r for r in results.values() if r['success']]
        if successful_nodes:
            total_throughput = sum(r['images_per_second'] for r in successful_nodes)
            avg_duration = statistics.mean(r['duration'] for r in successful_nodes)
            
            print(f"\n📊 AGGREGATE PERFORMANCE:")
            print(f"   Active nodes: {len(successful_nodes)}/{len(ports)}")
            print(f"   Total throughput: {total_throughput:.1f} img/s")
            print(f"   Avg duration: {avg_duration:.2f}s")
            print(f"   Theoretical max: {total_throughput * batch_size:,.0f} images/batch")
        
        return results
    
    def run_comprehensive_test(self):
        """Suite completa de pruebas"""
        print("🚀 ULTRA-FAST IMAGE PROCESSING - STRESS TEST")
        print("=" * 80)
        
        # Check server health
        try:
            health = requests.get(f"{self.base_url}/health", timeout=5)
            if health.status_code != 200:
                raise Exception("Server unhealthy")
            print("✅ Primary server online")
            
            # Get server info
            info = requests.get(f"{self.base_url}/info", timeout=5)
            if info.status_code == 200:
                root = ET.fromstring(info.text)
                max_batch = root.find('max_batch_size')
                if max_batch is not None:
                    print(f"📊 Server max batch size: {max_batch.text}")
        
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return {}
        
        # System info
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        print(f"💻 System: {cpu_count} cores, {memory_gb:.1f} GB RAM")
        
        all_results = {}
        
        # 1. Scalability test
        print(f"\n{'='*20} SCALABILITY TESTS {'='*20}")
        scalability_results = self.run_scalability_test()
        all_results['scalability'] = scalability_results
        
        # 2. Concurrent nodes test
        print(f"\n{'='*20} CONCURRENT NODES TEST {'='*20}")
        concurrent_results = self.run_concurrent_nodes_test()
        all_results['concurrent_nodes'] = concurrent_results
        
        # 3. Final summary
        self._print_final_summary(all_results)
        
        return all_results
    
    def _print_final_summary(self, results: Dict):
        """Resumen final de todas las pruebas"""
        print(f"\n{'='*80}")
        print("🏆 FINAL PERFORMANCE SUMMARY")
        print(f"{'='*80}")
        
        # Find best performances
        best_single_performance = 0
        best_batch_size = 0
        best_scenario = ""
        
        if 'scalability' in results:
            for scenario, scenario_results in results['scalability'].items():
                for batch_size, result in scenario_results.items():
                    if result['success'] and result['images_per_second'] > best_single_performance:
                        best_single_performance = result['images_per_second']
                        best_batch_size = batch_size
                        best_scenario = scenario
        
        if best_single_performance > 0:
            print(f"🥇 Best Single Node Performance:")
            print(f"   Scenario: {best_scenario}")
            print(f"   Batch size: {best_batch_size:,} images")
            print(f"   Speed: {best_single_performance:.1f} images/second")
            print(f"   Extrapolated daily capacity: {best_single_performance * 86400:,.0f} images")
        
        # Concurrent performance
        if 'concurrent_nodes' in results:
            concurrent = results['concurrent_nodes']
            successful_nodes = sum(1 for r in concurrent.values() if r['success'])
            total_throughput = sum(r['images_per_second'] for r in concurrent.values() if r['success'])
            
            if total_throughput > 0:
                print(f"\n🔗 Concurrent Nodes Performance:")
                print(f"   Active nodes: {successful_nodes}")
                print(f"   Combined throughput: {total_throughput:.1f} images/second")
                print(f"   Scaling efficiency: {total_throughput/successful_nodes/best_single_performance*100:.1f}%")
        
        # Recommendations
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        
        if best_single_performance < 100:
            print("   ⚠️  Low throughput detected:")
            print("      - Check system resources (CPU/RAM)")
            print("      - Optimize image processing pipeline")
            print("      - Consider SSD storage for temp files")
        
        if best_batch_size < 10000:
            print("   ⚠️  Limited batch size capacity:")
            print("      - Increase system RAM")
            print("      - Optimize memory management")
            print("      - Implement disk-based processing")
        
        print(f"\n✅ Testing completed successfully!")

def main():
    tester = UltraStressTest()
    results = tester.run_comprehensive_test()
    
    # Save results to file
    timestamp = int(time.time())
    filename = f"stress_test_results_{timestamp}.json"
    
    # Convert results to JSON-serializable format
    json_results = {}
    for key, value in results.items():
        if isinstance(value, dict):
            json_results[key] = {str(k): v for k, v in value.items()}
        else:
            json_results[key] = value
    
    try:
        with open(filename, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {filename}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")

if __name__ == "__main__":
    main()