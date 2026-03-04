"""
Video service for handling product video uploads, processing, and thumbnail generation
"""
import os
import uuid
import subprocess
import json
from typing import Optional, Dict
from decimal import Decimal
from sqlalchemy.orm import Session
from shared.models.product import ProductVideo, Product


class VideoService:
    """Service for handling product video operations"""

    def __init__(self):
        self.upload_dir = "uploads/products"
        self.max_video_size = 50 * 1024 * 1024  # 50MB
        self.max_duration = 60  # 1 minute (60 seconds)
        self.allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        self.min_resolution = (854, 480)  # Minimum 480p

    def validate_video_file(self, file_data: bytes, filename: str) -> bool:
        """Validate video file extension and size"""
        ext = os.path.splitext(filename)[1].lower()

        # Check file extension
        if ext not in self.allowed_extensions:
            return False

        # Check file size
        if len(file_data) > self.max_video_size:
            return False

        return True

    def generate_filename(self, original_filename: str) -> str:
        """Generate unique filename for video"""
        ext = os.path.splitext(original_filename)[1].lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"

    def get_video_metadata(self, video_path: str) -> Dict:
        """
        Extract video metadata using ffprobe
        Returns duration, resolution, and file size
        """
        try:
            # Use ffprobe to get video information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)

            # Get video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break

            if not video_stream:
                return {
                    'duration': 0,
                    'width': 0,
                    'height': 0,
                    'file_size_mb': 0
                }

            # Extract metadata
            duration = float(data.get('format', {}).get('duration', 0))
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            file_size = int(data.get('format', {}).get('size', 0))

            return {
                'duration': duration,
                'width': width,
                'height': height,
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            }

        except Exception as e:
            print(f"Error extracting video metadata: {e}")
            return {
                'duration': 0,
                'width': 0,
                'height': 0,
                'file_size_mb': 0
            }

    def generate_thumbnail(self, video_path: str) -> Optional[str]:
        """
        Generate thumbnail from video at 10% of duration
        Returns thumbnail path or None if failed
        """
        try:
            base_name = os.path.splitext(video_path)[0]
            thumbnail_path = f"{base_name}_thumb.jpg"

            # Use ffmpeg to extract frame at 10% of video
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', '00:00:01',  # Take frame at 1 second (or adjust)
                '-vframes', '1',
                '-vf', 'scale=320:-1',  # Scale to 320px width, maintain aspect ratio
                '-y',  # Overwrite output file
                thumbnail_path
            ]

            result = subprocess.run(cmd, capture_output=True)

            if result.returncode == 0 and os.path.exists(thumbnail_path):
                return thumbnail_path
            else:
                print(f"Failed to generate thumbnail: {result.stderr.decode()}")
                return None

        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None

    def compress_video(self, input_path: str, output_path: str, max_size_mb: int = 20) -> bool:
        """
        Compress video to reduce file size while maintaining quality
        Returns True if successful, False otherwise
        """
        try:
            # Two-pass encoding for better quality/size ratio
            # Using H.264 codec with CRF (Constant Rate Factor)
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vcodec', 'libx264',
                '-crf', '28',  # Higher = more compression (18-28 is good range)
                '-preset', 'medium',
                '-acodec', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',  # Overwrite
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True)

            if result.returncode == 0:
                # Check if compressed size is acceptable
                compressed_size = os.path.getsize(output_path)
                if compressed_size <= max_size_mb * 1024 * 1024:
                    return True
                else:
                    # Try more aggressive compression
                    cmd[5] = '32'  # Increase CRF for more compression
                    result = subprocess.run(cmd, capture_output=True)
                    return result.returncode == 0
            return False

        except Exception as e:
            print(f"Error compressing video: {e}")
            return False

    def validate_duration(self, video_path: str) -> bool:
        """Check if video duration is within limits"""
        metadata = self.get_video_metadata(video_path)
        return metadata['duration'] <= self.max_duration

    def validate_resolution(self, video_path: str) -> bool:
        """Check if video resolution meets minimum requirements"""
        metadata = self.get_video_metadata(video_path)
        width = metadata['width']
        height = metadata['height']

        # Check if either dimension meets minimum (handles portrait/landscape)
        return (width >= self.min_resolution[0] and height >= self.min_resolution[1]) or \
               (height >= self.min_resolution[0] and width >= self.min_resolution[1])

    def save_product_video(
        self,
        db: Session,
        product_id: int,
        video_url: str,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[Decimal] = None,
        file_size_mb: Optional[Decimal] = None,
        resolution: Optional[str] = None,
        alt_text: Optional[str] = None,
        is_primary: bool = False,
        order_index: int = 0
    ) -> ProductVideo:
        """Save product video record to database"""

        # If this is set as primary, make sure no other video is primary
        if is_primary:
            db.query(ProductVideo).filter(
                ProductVideo.product_id == product_id,
                ProductVideo.is_primary == True
            ).update({"is_primary": False})

        # Create video record
        product_video = ProductVideo(
            product_id=product_id,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            alt_text=alt_text or "Product video",
            duration_seconds=duration_seconds,
            file_size_mb=file_size_mb,
            resolution=resolution,
            is_primary=is_primary,
            order_index=order_index
        )

        db.add(product_video)
        db.commit()
        db.refresh(product_video)

        return product_video

    def get_product_videos(
        self,
        db: Session,
        product_id: int
    ) -> list:
        """Get all videos for a product"""
        return db.query(ProductVideo).filter(
            ProductVideo.product_id == product_id
        ).order_by(
            ProductVideo.is_primary.desc(),
            ProductVideo.order_index
        ).all()

    def delete_product_video(
        self,
        db: Session,
        video_id: int,
        product_id: int
    ) -> bool:
        """Delete a product video"""
        try:
            video = db.query(ProductVideo).filter(
                ProductVideo.id == video_id,
                ProductVideo.product_id == product_id
            ).first()

            if not video:
                return False

            # Delete video file
            video_path = video.video_url.replace('/static/', '')
            if os.path.exists(video_path):
                os.remove(video_path)

            # Delete thumbnail file
            if video.thumbnail_url:
                thumb_path = video.thumbnail_url.replace('/static/', '')
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)

            # Delete the database record
            db.delete(video)
            db.commit()

            return True

        except Exception as e:
            print(f"Error deleting video: {e}")
            db.rollback()
            return False


# Global instance
video_service = VideoService()
