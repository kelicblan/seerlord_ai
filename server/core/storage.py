import boto3
from botocore.exceptions import ClientError
from loguru import logger
from typing import Optional, Union
import os
from pathlib import Path
from server.core.config import settings

class S3Client:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Client, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.enabled = False
        if settings.S3_ENDPOINT and settings.S3_ACCESS_KEY_ID and settings.S3_SECRET_ACCESS_KEY:
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=settings.S3_ENDPOINT,
                    aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                    config=boto3.session.Config(s3={'addressing_style': 'path'}) if settings.S3_FORCE_PATH_STYLE else None
                )
                self.bucket_name = settings.S3_BUCKET_NAME
                self.enabled = True
                self._ensure_bucket_exists()
                logger.info(f"S3 Client initialized with endpoint {settings.S3_ENDPOINT}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
        else:
            logger.warning("S3 configuration missing. File storage will be local only (if applicable) or fail.")

    def _ensure_bucket_exists(self):
        if not self.enabled:
            return
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket {self.bucket_name}")
                except Exception as create_err:
                    logger.error(f"Failed to create bucket {self.bucket_name}: {create_err}")
                    self.enabled = False
            elif error_code == '403':
                logger.warning(f"403 Forbidden checking bucket {self.bucket_name}. Assuming it exists and continuing.")
            else:
                logger.error(f"Error checking bucket {self.bucket_name}: {e}")
                self.enabled = False

    def upload_file(self, file_data: Union[bytes, str, Path], object_name: str, content_type: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to S3 and return the public URL.
        file_data: can be bytes, string content, or Path to a file.
        """
        if not self.enabled:
            logger.warning("S3 is not enabled. Skipping upload.")
            return None

        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            else:
                # Try to guess content type from object name
                import mimetypes
                guessed_type, _ = mimetypes.guess_type(object_name)
                if guessed_type:
                    extra_args['ContentType'] = guessed_type

            if isinstance(file_data, (str, Path)) and os.path.isfile(file_data):
                 # It's a file path
                self.client.upload_file(str(file_data), self.bucket_name, object_name, ExtraArgs=extra_args)
            elif isinstance(file_data, bytes):
                from io import BytesIO
                self.client.upload_fileobj(BytesIO(file_data), self.bucket_name, object_name, ExtraArgs=extra_args)
            elif isinstance(file_data, str):
                 # It's string content
                from io import BytesIO
                self.client.upload_fileobj(BytesIO(file_data.encode('utf-8')), self.bucket_name, object_name, ExtraArgs=extra_args)
            else:
                logger.error(f"Unsupported file_data type: {type(file_data)}")
                return None

            # Generate URL
            # Assumes public read or pre-signed. For now, we construct the URL based on endpoint.
            # If endpoint is a domain like https://files.seerlord.cn, and path style is true:
            # https://files.seerlord.cn/bucket_name/object_name
            
            url = f"{settings.S3_ENDPOINT}/{self.bucket_name}/{object_name}"
            return url

        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return None

    def get_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL to share an S3 object.
        """
        if not self.enabled:
            return None

        try:
            response = self.client.generate_presigned_url('get_object',
                                                        Params={'Bucket': self.bucket_name,
                                                                'Key': object_name},
                                                        ExpiresIn=expiration)
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

s3_client = S3Client()
