"""
List repository for database operations
"""
from typing import Optional, List as TypeList
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from uuid import UUID

from models.list import List, ListItem
from models.report import Report


class ListRepository:
    """Repository for List operations"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== List Operations ====================

    def get_by_id(self, list_id: UUID, include_items: bool = False) -> Optional[List]:
        """Get list by ID"""
        query = self.db.query(List).filter(List.id == list_id)
        if include_items:
            query = query.options(joinedload(List.items))
        return query.first()

    def get_all(
        self,
        tenant_id: UUID,
        list_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> TypeList[List]:
        """Get all lists for a tenant"""
        query = self.db.query(List).filter(List.tenant_id == tenant_id)

        if list_type:
            query = query.filter(List.list_type == list_type)

        return (
            query
            .options(joinedload(List.creator))
            .order_by(desc(List.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self, tenant_id: UUID, list_type: Optional[str] = None) -> int:
        """Count lists for a tenant"""
        query = self.db.query(func.count(List.id)).filter(List.tenant_id == tenant_id)
        if list_type:
            query = query.filter(List.list_type == list_type)
        return query.scalar() or 0

    def create(self, **kwargs) -> List:
        """Create a new list"""
        new_list = List(**kwargs)
        self.db.add(new_list)
        self.db.commit()
        self.db.refresh(new_list)
        return new_list

    def update(self, list_id: UUID, **kwargs) -> Optional[List]:
        """Update a list"""
        list_obj = self.get_by_id(list_id)
        if list_obj:
            for key, value in kwargs.items():
                setattr(list_obj, key, value)
            self.db.commit()
            self.db.refresh(list_obj)
        return list_obj

    def delete(self, list_id: UUID) -> bool:
        """Delete a list (cascade deletes items)"""
        list_obj = self.get_by_id(list_id)
        if list_obj:
            self.db.delete(list_obj)
            self.db.commit()
            return True
        return False

    # ==================== List Item Operations ====================

    def get_item(self, list_id: UUID, item_id: UUID) -> Optional[ListItem]:
        """Get a specific item in a list"""
        return (
            self.db.query(ListItem)
            .filter(ListItem.list_id == list_id, ListItem.item_id == item_id)
            .first()
        )

    def get_items(
        self,
        list_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> TypeList[ListItem]:
        """Get all items in a list"""
        return (
            self.db.query(ListItem)
            .filter(ListItem.list_id == list_id)
            .order_by(desc(ListItem.added_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_items(self, list_id: UUID) -> int:
        """Count items in a list"""
        return (
            self.db.query(func.count(ListItem.id))
            .filter(ListItem.list_id == list_id)
            .scalar() or 0
        )

    def add_item(self, list_id: UUID, item_id: UUID, added_by: Optional[UUID] = None) -> Optional[ListItem]:
        """Add an item to a list (returns None if already exists)"""
        # Check if already exists
        existing = self.get_item(list_id, item_id)
        if existing:
            return None

        item = ListItem(
            list_id=list_id,
            item_id=item_id,
            added_by=added_by,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_items(
        self,
        list_id: UUID,
        item_ids: TypeList[UUID],
        added_by: Optional[UUID] = None
    ) -> TypeList[ListItem]:
        """Add multiple items to a list (skips duplicates)"""
        added = []
        for item_id in item_ids:
            item = self.add_item(list_id, item_id, added_by)
            if item:
                added.append(item)
        return added

    def add_items_to_multiple_lists(
        self,
        list_ids: TypeList[UUID],
        item_ids: TypeList[UUID],
        added_by: Optional[UUID] = None
    ) -> dict:
        """Add multiple items to multiple lists (for multi-select add)"""
        results = {}
        for list_id in list_ids:
            results[str(list_id)] = self.add_items(list_id, item_ids, added_by)
        return results

    def remove_item(self, list_id: UUID, item_id: UUID) -> bool:
        """Remove an item from a list"""
        item = self.get_item(list_id, item_id)
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False

    def remove_items(self, list_id: UUID, item_ids: TypeList[UUID]) -> int:
        """Remove multiple items from a list"""
        count = (
            self.db.query(ListItem)
            .filter(ListItem.list_id == list_id, ListItem.item_id.in_(item_ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return count

    # ==================== Query Helpers ====================

    def get_lists_containing_item(self, tenant_id: UUID, item_id: UUID) -> TypeList[List]:
        """Get all lists that contain a specific item"""
        return (
            self.db.query(List)
            .join(ListItem)
            .filter(List.tenant_id == tenant_id, ListItem.item_id == item_id)
            .all()
        )

    def get_reports_in_list(self, list_id: UUID, skip: int = 0, limit: int = 100) -> TypeList[Report]:
        """Get all reports in a list (for report-type lists)"""
        return (
            self.db.query(Report)
            .join(ListItem, Report.id == ListItem.item_id)
            .filter(ListItem.list_id == list_id)
            .order_by(desc(ListItem.added_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_list_with_reports(self, list_id: UUID) -> Optional[dict]:
        """Get a list with its report items fully loaded"""
        list_obj = self.get_by_id(list_id, include_items=True)
        if not list_obj:
            return None

        if list_obj.list_type != 'report':
            return list_obj.to_dict(include_items=True)

        # For report lists, get full report data
        reports = self.get_reports_in_list(list_id)
        result = list_obj.to_dict()
        result['reports'] = [r.to_dict() for r in reports]
        return result
