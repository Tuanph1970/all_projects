"""
Image service for handling product images, uploads, and processing
"""
import os
import io
import uuid
from typing import List, Optional
from PIL import Image
from sqlalchemy.orm import Session
from app.models.product import ProductImage, Product
from app.core.config import settings

class ImageService:
    """Service for handling product image operations"""
    
    def __init__(self):
        self.upload_dir = "uploads/products"
        self.max_file_size = 50 * 1024 * 1024  # 50MB for videos, 5MB for images
        self.max_image_size = 5 * 1024 * 1024  # 5MB for images
        self.allowed_image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        self.allowed_video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        self.allowed_extensions = self.allowed_image_extensions | self.allowed_video_extensions
        self.thumbnail_sizes = {
            'small': (150, 150),
            'medium': (300, 300),
            'large': (800, 800)
        }
    
    def validate_media_file(self, file_data: bytes, filename: str) -> bool:
        """Validate image or video file"""
        ext = os.path.splitext(filename)[1].lower()
        
        # Check file extension
        if ext not in self.allowed_extensions:
            return False
        
        # Check file size based on type
        if ext in self.allowed_image_extensions:
            if len(file_data) > self.max_image_size:
                return False
            try:
                # Validate that it's a real image
                Image.open(io.BytesIO(file_data))
                return True
            except Exception:
                return False
        elif ext in self.allowed_video_extensions:
            if len(file_data) > self.max_file_size:
                return False
            # For videos, just check file size and extension
            # You could add more sophisticated video validation here
            return True
        
        return False
    
    # Keep the old method for backward compatibility
    def validate_image(self, file_data: bytes, filename: str) -> bool:
        """Validate image file - backward compatibility"""
        return self.validate_media_file(file_data, filename)
    
    def generate_filename(self, original_filename: str) -> str:
        """Generate unique filename"""
        ext = os.path.splitext(original_filename)[1].lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"
    
    def create_thumbnails(self, image_path: str) -> dict:
        """Create thumbnail versions of image"""
        thumbnails = {}
        
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                base_name = os.path.splitext(image_path)[0]
                
                for size_name, (width, height) in self.thumbnail_sizes.items():
                    # Create thumbnail
                    thumbnail = img.copy()
                    thumbnail.thumbnail((width, height), Image.Resampling.LANCZOS)
                    
                    # Save thumbnail
                    thumb_path = f"{base_name}_{size_name}.jpg"
                    thumbnail.save(thumb_path, 'JPEG', quality=85, optimize=True)
                    
                    thumbnails[size_name] = thumb_path
                    
        except Exception as e:
            print(f"Error creating thumbnails: {e}")
        
        return thumbnails
    
    def save_product_image(
        self, 
        db: Session, 
        product_id: int, 
        image_url: str,
        alt_text: Optional[str] = None,
        is_primary: bool = False,
        order_index: int = 0
    ) -> ProductImage:
        """Save product image record to database"""
        
        # If this is set as primary, make sure no other image is primary
        if is_primary:
            db.query(ProductImage).filter(
                ProductImage.product_id == product_id,
                ProductImage.is_primary == True
            ).update({"is_primary": False})
        
        # Create image record
        product_image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            alt_text=alt_text or f"Product image {order_index + 1}",
            is_primary=is_primary,
            order_index=order_index
        )
        
        db.add(product_image)
        db.commit()
        db.refresh(product_image)
        
        return product_image
    
    def reorder_product_images(
        self, 
        db: Session, 
        product_id: int, 
        image_order: List[int]
    ) -> bool:
        """Reorder product images"""
        try:
            for index, image_id in enumerate(image_order):
                db.query(ProductImage).filter(
                    ProductImage.id == image_id,
                    ProductImage.product_id == product_id
                ).update({"order_index": index})
            
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    
    def set_primary_image(
        self, 
        db: Session, 
        product_id: int, 
        image_id: int
    ) -> bool:
        """Set an image as primary for a product"""
        try:
            # Remove primary flag from all images
            db.query(ProductImage).filter(
                ProductImage.product_id == product_id
            ).update({"is_primary": False})
            
            # Set new primary image
            result = db.query(ProductImage).filter(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id
            ).update({"is_primary": True})
            
            if result:
                db.commit()
                return True
            else:
                db.rollback()
                return False
                
        except Exception:
            db.rollback()
            return False
    
    def delete_product_image(
        self, 
        db: Session, 
        product_id: int, 
        image_id: int
    ) -> bool:
        """Delete a product image"""
        try:
            image = db.query(ProductImage).filter(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id
            ).first()
            
            if not image:
                return False
            
            was_primary = image.is_primary
            
            # Delete the image record
            db.delete(image)
            
            # If this was the primary image, set another as primary
            if was_primary:
                next_image = db.query(ProductImage).filter(
                    ProductImage.product_id == product_id
                ).order_by(ProductImage.order_index).first()
                
                if next_image:
                    next_image.is_primary = True
            
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            return False
    
    def get_product_images(
        self, 
        db: Session, 
        product_id: int
    ) -> List[ProductImage]:
        """Get all images for a product"""
        return db.query(ProductImage).filter(
            ProductImage.product_id == product_id
        ).order_by(
            ProductImage.is_primary.desc(),
            ProductImage.order_index
        ).all()
    
    def optimize_image_loading(
        self, 
        images: List[ProductImage]
    ) -> dict:
        """Optimize image loading with different sizes"""
        optimized = {
            'primary': None,
            'gallery': [],
            'thumbnails': []
        }
        
        for image in images:
            image_data = {
                'id': image.id,
                'url': image.image_url,
                'alt_text': image.alt_text,
                'is_primary': image.is_primary,
                'order_index': image.order_index
            }
            
            if image.is_primary:
                optimized['primary'] = image_data
            
            optimized['gallery'].append(image_data)
            
            # Add thumbnail URL (assuming naming convention)
            base_url = os.path.splitext(image.image_url)[0]
            image_data['thumbnails'] = {
                'small': f"{base_url}_small.jpg",
                'medium': f"{base_url}_medium.jpg", 
                'large': f"{base_url}_large.jpg"
            }
            optimized['thumbnails'].append(image_data)
        
        return optimized

# Global instance
image_service = ImageService()