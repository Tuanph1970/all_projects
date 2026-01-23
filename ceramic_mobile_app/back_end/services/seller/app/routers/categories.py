"""
Seller Category Management Router
Provides full CRUD operations for seller-specific product categories
with tree structure support (max 4 levels)

All operations are isolated to the current seller's categories.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
from typing import List, Optional
from datetime import datetime
import re

from shared.database import get_db
from shared.security import get_current_user
from shared.models.user import User, UserRole
from shared.models.seller_category import SellerCategory

from app.schemas.seller_category import (
    SellerCategoryCreate,
    SellerCategoryUpdate,
    SellerCategoryResponse,
    SellerCategoryTreeNode,
    SellerCategoryTreeResponse,
    SellerCategoryListResponse,
    CategoryReorderRequest,
    CategoryMoveRequest,
    CategoryBulkActionRequest,
    CategoryBulkActionResponse,
    CategoryPathResponse,
    CategoryStatsResponse,
    SellerCategoryBrief
)

router = APIRouter()

MAX_CATEGORY_DEPTH = 4


def require_seller(current_user: User) -> User:
    """Verify user has seller role"""
    if current_user.role not in [UserRole.SELLER, UserRole.DUAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can manage categories"
        )
    return current_user


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name"""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:120]


def calculate_level(parent: Optional[SellerCategory]) -> int:
    """Calculate the level for a new category based on parent"""
    if parent is None:
        return 1
    return parent.level + 1


def validate_parent_depth(parent: SellerCategory, db: Session) -> None:
    """Validate that adding a child won't exceed max depth"""
    if parent.level >= MAX_CATEGORY_DEPTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create subcategory: maximum depth of {MAX_CATEGORY_DEPTH} levels reached"
        )


def build_category_tree(categories: List[SellerCategory], parent_id: Optional[int] = None) -> List[SellerCategoryTreeNode]:
    """Recursively build tree structure from flat category list"""
    tree = []
    for category in categories:
        if category.parent_id == parent_id:
            node = SellerCategoryTreeNode(
                id=category.id,
                seller_id=category.seller_id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                parent_id=category.parent_id,
                level=category.level,
                path=category.path,
                display_order=category.display_order,
                icon_url=category.icon_url,
                image_url=category.image_url,
                is_active=category.is_active,
                product_count=category.product_count,
                created_at=category.created_at,
                updated_at=category.updated_at,
                children=build_category_tree(categories, category.id),
                full_path_name=category.get_full_path_name()
            )
            tree.append(node)
    # Sort by display_order
    tree.sort(key=lambda x: x.display_order)
    return tree


def update_children_paths(category: SellerCategory, db: Session) -> None:
    """Recursively update path for all children when parent moves"""
    category.update_path()
    for child in category.children:
        update_children_paths(child, db)


def update_children_levels(category: SellerCategory, new_level: int, db: Session) -> None:
    """Recursively update level for all descendants"""
    category.level = new_level
    for child in category.children:
        if new_level >= MAX_CATEGORY_DEPTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Moving would cause children to exceed maximum depth of {MAX_CATEGORY_DEPTH}"
            )
        update_children_levels(child, new_level + 1, db)


# ============================================================
# CRUD ENDPOINTS
# ============================================================

@router.get("/categories", response_model=SellerCategoryListResponse)
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    parent_id: Optional[int] = Query(None, description="Filter by parent ID (null for root)"),
    level: Optional[int] = Query(None, ge=1, le=4, description="Filter by level"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name")
):
    """
    List seller's categories with pagination and filters.
    Returns flat list (use /categories/tree for hierarchical view).
    """
    require_seller(current_user)

    query = db.query(SellerCategory).filter(
        SellerCategory.seller_id == current_user.id
    )

    # Apply filters
    if parent_id is not None:
        query = query.filter(SellerCategory.parent_id == parent_id)
    elif parent_id is None and level == 1:
        query = query.filter(SellerCategory.parent_id == None)

    if level is not None:
        query = query.filter(SellerCategory.level == level)

    if is_active is not None:
        query = query.filter(SellerCategory.is_active == is_active)

    if search:
        query = query.filter(SellerCategory.name.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    categories = query.order_by(
        SellerCategory.level,
        SellerCategory.display_order,
        SellerCategory.name
    ).offset((page - 1) * page_size).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size

    return SellerCategoryListResponse(
        items=categories,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/categories/tree", response_model=SellerCategoryTreeResponse)
def get_category_tree(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive categories")
):
    """
    Get full category tree structure for the seller.
    Returns hierarchical nested structure.
    """
    require_seller(current_user)

    query = db.query(SellerCategory).filter(
        SellerCategory.seller_id == current_user.id
    )

    if not include_inactive:
        query = query.filter(SellerCategory.is_active == True)

    categories = query.order_by(
        SellerCategory.level,
        SellerCategory.display_order,
        SellerCategory.name
    ).all()

    tree = build_category_tree(categories)

    return SellerCategoryTreeResponse(
        categories=tree,
        total_count=len(categories),
        max_level=MAX_CATEGORY_DEPTH
    )


@router.get("/categories/roots", response_model=List[SellerCategoryResponse])
def get_root_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive categories")
):
    """Get all root-level categories (level 1) for the seller"""
    require_seller(current_user)

    query = db.query(SellerCategory).filter(
        and_(
            SellerCategory.seller_id == current_user.id,
            SellerCategory.parent_id == None
        )
    )

    if not include_inactive:
        query = query.filter(SellerCategory.is_active == True)

    categories = query.order_by(
        SellerCategory.display_order,
        SellerCategory.name
    ).all()

    return categories


@router.get("/categories/stats", response_model=CategoryStatsResponse)
def get_category_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics about seller's categories"""
    require_seller(current_user)

    base_query = db.query(SellerCategory).filter(
        SellerCategory.seller_id == current_user.id
    )

    total = base_query.count()
    active = base_query.filter(SellerCategory.is_active == True).count()
    roots = base_query.filter(SellerCategory.parent_id == None).count()

    # Get max depth used
    max_depth_result = db.query(func.max(SellerCategory.level)).filter(
        SellerCategory.seller_id == current_user.id
    ).scalar()
    max_depth = max_depth_result or 0

    # Count by level
    level_counts = db.query(
        SellerCategory.level,
        func.count(SellerCategory.id)
    ).filter(
        SellerCategory.seller_id == current_user.id
    ).group_by(SellerCategory.level).all()

    categories_by_level = {level: count for level, count in level_counts}

    return CategoryStatsResponse(
        total_categories=total,
        active_categories=active,
        root_categories=roots,
        max_depth_used=max_depth,
        categories_by_level=categories_by_level
    )


@router.get("/categories/{category_id}", response_model=SellerCategoryTreeNode)
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_children: bool = Query(True, description="Include child categories")
):
    """Get a single category by ID with optional children"""
    require_seller(current_user)

    category = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id == category_id,
            SellerCategory.seller_id == current_user.id
        )
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    children = []
    if include_children:
        # Get all descendants for building subtree
        all_descendants = db.query(SellerCategory).filter(
            and_(
                SellerCategory.seller_id == current_user.id,
                SellerCategory.path.like(f"{category.path}/%")
            )
        ).order_by(SellerCategory.level, SellerCategory.display_order).all()

        children = build_category_tree([category] + all_descendants, category.parent_id)
        if children:
            children = children[0].children  # Get children of the requested category

    return SellerCategoryTreeNode(
        id=category.id,
        seller_id=category.seller_id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        parent_id=category.parent_id,
        level=category.level,
        path=category.path,
        display_order=category.display_order,
        icon_url=category.icon_url,
        image_url=category.image_url,
        is_active=category.is_active,
        product_count=category.product_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
        children=children,
        full_path_name=category.get_full_path_name()
    )


@router.get("/categories/{category_id}/path", response_model=CategoryPathResponse)
def get_category_path(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the breadcrumb path from root to the specified category"""
    require_seller(current_user)

    category = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id == category_id,
            SellerCategory.seller_id == current_user.id
        )
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Build path from root to current
    path = []
    current = category.parent
    while current:
        path.insert(0, SellerCategoryBrief(
            id=current.id,
            name=current.name,
            slug=current.slug,
            level=current.level,
            is_active=current.is_active,
            product_count=current.product_count
        ))
        current = current.parent

    return CategoryPathResponse(
        path=path,
        current=category
    )


@router.get("/categories/{category_id}/children", response_model=List[SellerCategoryResponse])
def get_category_children(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_inactive: bool = Query(False, description="Include inactive categories")
):
    """Get direct children of a category"""
    require_seller(current_user)

    # Verify parent exists and belongs to seller
    parent = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id == category_id,
            SellerCategory.seller_id == current_user.id
        )
    ).first()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    query = db.query(SellerCategory).filter(
        and_(
            SellerCategory.seller_id == current_user.id,
            SellerCategory.parent_id == category_id
        )
    )

    if not include_inactive:
        query = query.filter(SellerCategory.is_active == True)

    children = query.order_by(
        SellerCategory.display_order,
        SellerCategory.name
    ).all()

    return children


@router.post("/categories", response_model=SellerCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: SellerCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new category for the seller.
    Parent category must belong to the same seller and be below max depth.
    """
    require_seller(current_user)

    parent = None
    level = 1

    # Validate parent if provided
    if category_data.parent_id is not None:
        parent = db.query(SellerCategory).filter(
            and_(
                SellerCategory.id == category_data.parent_id,
                SellerCategory.seller_id == current_user.id
            )
        ).first()

        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )

        validate_parent_depth(parent, db)
        level = parent.level + 1

    # Check for duplicate name under same parent
    existing = db.query(SellerCategory).filter(
        and_(
            SellerCategory.seller_id == current_user.id,
            SellerCategory.parent_id == category_data.parent_id,
            SellerCategory.name == category_data.name
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A category with this name already exists under the same parent"
        )

    # Generate slug if not provided
    slug = category_data.slug or generate_slug(category_data.name)

    # Get max display order for siblings
    max_order = db.query(func.max(SellerCategory.display_order)).filter(
        and_(
            SellerCategory.seller_id == current_user.id,
            SellerCategory.parent_id == category_data.parent_id
        )
    ).scalar()
    display_order = (max_order or 0) + 1 if category_data.display_order == 0 else category_data.display_order

    # Create category
    category = SellerCategory(
        seller_id=current_user.id,
        name=category_data.name,
        slug=slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
        level=level,
        display_order=display_order,
        icon_url=category_data.icon_url,
        image_url=category_data.image_url,
        is_active=category_data.is_active
    )

    try:
        db.add(category)
        db.flush()  # Get the ID

        # Update path
        if parent:
            parent_path = parent.path or str(parent.id)
            category.path = f"{parent_path}/{category.id}"
        else:
            category.path = str(category.id)

        db.commit()
        db.refresh(category)
        return category

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create category: {str(e)}"
        )


@router.put("/categories/{category_id}", response_model=SellerCategoryResponse)
def update_category(
    category_id: int,
    category_data: SellerCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing category"""
    require_seller(current_user)

    category = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id == category_id,
            SellerCategory.seller_id == current_user.id
        )
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    update_data = category_data.model_dump(exclude_unset=True)

    # Handle parent change (moving category)
    if 'parent_id' in update_data and update_data['parent_id'] != category.parent_id:
        new_parent_id = update_data['parent_id']

        # Prevent setting self as parent
        if new_parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )

        # Validate new parent
        new_parent = None
        new_level = 1

        if new_parent_id is not None:
            new_parent = db.query(SellerCategory).filter(
                and_(
                    SellerCategory.id == new_parent_id,
                    SellerCategory.seller_id == current_user.id
                )
            ).first()

            if not new_parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New parent category not found"
                )

            # Prevent circular reference (moving to own descendant)
            if new_parent.path and category.path and new_parent.path.startswith(f"{category.path}/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot move category to its own descendant"
                )

            new_level = new_parent.level + 1

        # Check if move would exceed max depth
        max_child_depth = db.query(func.max(SellerCategory.level)).filter(
            SellerCategory.path.like(f"{category.path}/%")
        ).scalar()

        if max_child_depth:
            depth_increase = new_level - category.level
            if max_child_depth + depth_increase > MAX_CATEGORY_DEPTH:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Moving would cause descendants to exceed maximum depth of {MAX_CATEGORY_DEPTH}"
                )

        # Update level and path for this category and all descendants
        old_level = category.level
        category.parent_id = new_parent_id
        category.level = new_level

        # Update path
        if new_parent:
            parent_path = new_parent.path or str(new_parent.id)
            category.path = f"{parent_path}/{category.id}"
        else:
            category.path = str(category.id)

        # Update all descendants
        update_children_levels(category, new_level, db)
        update_children_paths(category, db)

        # Remove parent_id from update_data as we've handled it
        del update_data['parent_id']

    # Check for duplicate name if name is being changed
    if 'name' in update_data and update_data['name'] != category.name:
        existing = db.query(SellerCategory).filter(
            and_(
                SellerCategory.seller_id == current_user.id,
                SellerCategory.parent_id == category.parent_id,
                SellerCategory.name == update_data['name'],
                SellerCategory.id != category_id
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A category with this name already exists under the same parent"
            )

    # Update remaining fields
    for field, value in update_data.items():
        if hasattr(category, field):
            setattr(category, field, value)

    # Auto-update slug if name changed and slug not explicitly set
    if 'name' in update_data and 'slug' not in update_data:
        category.slug = generate_slug(update_data['name'])

    category.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(category)
        return category
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update category: {str(e)}"
        )


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cascade: bool = Query(False, description="Delete all child categories too")
):
    """
    Delete a category.
    By default, fails if category has children. Use cascade=true to delete all descendants.
    """
    require_seller(current_user)

    category = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id == category_id,
            SellerCategory.seller_id == current_user.id
        )
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check for children
    children_count = db.query(SellerCategory).filter(
        SellerCategory.parent_id == category_id
    ).count()

    if children_count > 0 and not cascade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category has {children_count} child categories. Use cascade=true to delete all descendants."
        )

    # Check if products are using this category
    # (This would require a relationship to a seller_product_category mapping table)
    # For now, we'll allow deletion

    try:
        if cascade:
            # Delete all descendants (cascade is handled by FK on delete)
            pass  # SQLAlchemy cascade will handle this

        db.delete(category)
        db.commit()

        return {
            "message": "Category deleted successfully",
            "deleted_id": category_id,
            "cascade": cascade
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete category: {str(e)}"
        )


# ============================================================
# BULK & SPECIAL OPERATIONS
# ============================================================

@router.put("/categories/reorder", response_model=dict)
def reorder_categories(
    reorder_data: CategoryReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reorder multiple categories at once"""
    require_seller(current_user)

    category_ids = [item.id for item in reorder_data.items]

    # Verify all categories belong to seller
    categories = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id.in_(category_ids),
            SellerCategory.seller_id == current_user.id
        )
    ).all()

    if len(categories) != len(category_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some categories not found or don't belong to you"
        )

    category_map = {c.id: c for c in categories}

    try:
        for item in reorder_data.items:
            category = category_map[item.id]
            category.display_order = item.display_order

            # Handle parent change if provided
            if item.parent_id is not None and item.parent_id != category.parent_id:
                # Validate new parent
                if item.parent_id == item.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Category {item.id} cannot be its own parent"
                    )

                new_parent = db.query(SellerCategory).filter(
                    and_(
                        SellerCategory.id == item.parent_id,
                        SellerCategory.seller_id == current_user.id
                    )
                ).first()

                if not new_parent:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Parent category {item.parent_id} not found"
                    )

                if new_parent.level >= MAX_CATEGORY_DEPTH:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot move category {item.id}: would exceed max depth"
                    )

                category.parent_id = item.parent_id
                category.level = new_parent.level + 1

            category.updated_at = datetime.utcnow()

        db.commit()

        return {
            "message": "Categories reordered successfully",
            "updated_count": len(reorder_data.items)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder categories: {str(e)}"
        )


@router.post("/categories/{category_id}/move", response_model=SellerCategoryResponse)
def move_category(
    category_id: int,
    move_data: CategoryMoveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Move a category to a new parent"""
    require_seller(current_user)

    # Use update endpoint with parent_id change
    update_data = SellerCategoryUpdate(parent_id=move_data.new_parent_id)
    return update_category(category_id, update_data, current_user, db)


@router.post("/categories/bulk-action", response_model=CategoryBulkActionResponse)
def bulk_category_action(
    action_data: CategoryBulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform bulk actions on multiple categories"""
    require_seller(current_user)

    valid_actions = ['activate', 'deactivate', 'delete']
    if action_data.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Must be one of: {valid_actions}"
        )

    categories = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id.in_(action_data.category_ids),
            SellerCategory.seller_id == current_user.id
        )
    ).all()

    found_ids = {c.id for c in categories}
    failed_ids = [id for id in action_data.category_ids if id not in found_ids]

    try:
        affected_count = 0

        if action_data.action == 'activate':
            for category in categories:
                category.is_active = True
                category.updated_at = datetime.utcnow()
                affected_count += 1

        elif action_data.action == 'deactivate':
            for category in categories:
                category.is_active = False
                category.updated_at = datetime.utcnow()
                affected_count += 1

        elif action_data.action == 'delete':
            for category in categories:
                # Check for children
                children_count = db.query(SellerCategory).filter(
                    SellerCategory.parent_id == category.id
                ).count()
                if children_count > 0:
                    failed_ids.append(category.id)
                else:
                    db.delete(category)
                    affected_count += 1

        db.commit()

        return CategoryBulkActionResponse(
            success=len(failed_ids) == 0,
            affected_count=affected_count,
            message=f"Successfully {action_data.action}d {affected_count} categories",
            failed_ids=failed_ids
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk action: {str(e)}"
        )


@router.post("/categories/{category_id}/duplicate", response_model=SellerCategoryResponse)
def duplicate_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_children: bool = Query(False, description="Duplicate child categories too")
):
    """Duplicate a category (optionally with children)"""
    require_seller(current_user)

    source = db.query(SellerCategory).filter(
        and_(
            SellerCategory.id == category_id,
            SellerCategory.seller_id == current_user.id
        )
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Create duplicate
    new_category = SellerCategory(
        seller_id=current_user.id,
        name=f"{source.name} (Copy)",
        slug=f"{source.slug}-copy" if source.slug else None,
        description=source.description,
        parent_id=source.parent_id,
        level=source.level,
        display_order=source.display_order + 1,
        icon_url=source.icon_url,
        image_url=source.image_url,
        is_active=False  # Start as inactive
    )

    try:
        db.add(new_category)
        db.flush()

        # Update path
        if source.parent:
            parent_path = source.parent.path or str(source.parent.id)
            new_category.path = f"{parent_path}/{new_category.id}"
        else:
            new_category.path = str(new_category.id)

        # TODO: If include_children, recursively duplicate children

        db.commit()
        db.refresh(new_category)
        return new_category

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate category: {str(e)}"
        )
