from abc import ABC, abstractmethod
import requests
import cv2
from ..common.config import cfg

class BaseOcrService(ABC):
    """公式识别服务的抽象基类"""
    
    @abstractmethod
    def recognize(self, image_data):
        """
        识别图片中的公式
        Args:
            image_data: OpenCV格式的图像数据
        Returns:
            dict: {
                'status': bool,      # 识别是否成功
                'latex': str,        # LaTeX公式
                'confidence': float, # 置信度
                'request_id': str,   # 请求ID
                'message': str       # 错误信息（如果有）
            }
        """
        pass

class SimpletexService(BaseOcrService):
    """Simpletex的公式识别服务实现"""
    
    def recognize(self, image_data):
        try:
            # 将图像编码为二进制
            _, img_encoded = cv2.imencode('.png', image_data)
            
            # 构造请求参数
            files = [('file', ('formula.png', img_encoded.tobytes(), 'image/png'))]
            headers = {'token': cfg.token.value}
            
            # 发送请求
            response = requests.post(
                cfg.api_url.value,
                files=files,
                headers=headers
            )
            
            # 解析响应
            result = response.json()
            
            if result.get('status') is True:
                res_data = result.get('res', {})
                return {
                    'status': True,
                    'latex': res_data.get('latex', ''),
                    'confidence': float(res_data.get('conf', 0)),
                    'request_id': result.get('request_id', ''),
                    'message': None
                }
            else:
                return {
                    'status': False,
                    'latex': None,
                    'confidence': 0,
                    'request_id': None,
                    'message': result.get('message', '未知错误')
                }
                
        except Exception as e:
            return {
                'status': False,
                'latex': None,
                'confidence': 0,
                'request_id': None,
                'message': str(e)
            }

class OcrServiceFactory:
    """公式识别服务工厂类"""
    
    @staticmethod
    def create_service():
        """
        根据配置创建对应的识别服务
        Returns:
            BaseOcrService: 识别服务实例
        """
        service_type = cfg.type.value
        
        if service_type == 'Simpletex':
            return SimpletexService()
        # 在这里添加其他服务的实现
        else:
            raise ValueError(f'Unsupported OCR service type: {service_type}') 