from flask import request, current_app
from flask_restful import Resource, marshal_with, fields, reqparse  # type: ignore
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from controllers.console import api
from extensions.ext_database import db
from libs.helper import TimestampField, uuid_value
from models import Dataset, App, Account, InstalledApp, TenantAccountJoin, DatasetPermission
from models.model import AppMode
from models.dataset import DatasetPermissionEnum
from models.types import StringUUID


class EmailDatasetsApi(Resource):
    """API to get datasets by user email"""
    
    dataset_fields = {
        'id': fields.String,
        'name': fields.String,
        'description': fields.String,
        'permission': fields.String,
        'provider': fields.String,
        'document_count': fields.Integer,
        'indexing_technique': fields.String,
        'created_by': fields.String,
        'created_at': TimestampField,
        'updated_by': fields.String,
        'updated_at': TimestampField,
    }
    
    response_fields = {
        'data': fields.List(fields.Nested(dataset_fields)),
        'has_more': fields.Boolean,
        'total': fields.Integer,
        'page': fields.Integer,
        'limit': fields.Integer
    }
    
    @marshal_with(response_fields)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, location='args')
        parser.add_argument('page', type=int, default=1, location='args')
        parser.add_argument('limit', type=int, default=20, location='args')
        args = parser.parse_args()
        
        email = args['email']
        page = args['page']
        limit = args['limit']
        offset = (page - 1) * limit
        
        # Find the account
        account = db.session.query(Account).filter(Account.email == email).first()
        
        current_app.logger.info(f"Looking up account for email {email}: {account.id if account else 'Not found'}")
        
        if not account:
            return {
                'data': [],
                'has_more': False,
                'total': 0,
                'page': page,
                'limit': limit
            }
            
        # Get current tenant
        tenant_account = db.session.query(TenantAccountJoin).filter(
            TenantAccountJoin.account_id == account.id,
            TenantAccountJoin.current == True
        ).first()
        
        if not tenant_account:
            # Try to get any tenant
            tenant_account = db.session.query(TenantAccountJoin).filter(
                TenantAccountJoin.account_id == account.id
            ).first()
            
        current_app.logger.info(f"Found tenant for account: {tenant_account.tenant_id if tenant_account else 'Not found'}")
            
        if not tenant_account:
            return {
                'data': [],
                'has_more': False,
                'total': 0,
                'page': page,
                'limit': limit
            }
        
        # Get all datasets created by the user or shared with them
        query = db.session.query(Dataset).filter(
            and_(
                Dataset.tenant_id == tenant_account.tenant_id,
                (
                    # Datasets created by the user
                    (Dataset.created_by == account.id) |
                    # Datasets shared with all team members
                    (Dataset.permission == DatasetPermissionEnum.ALL_TEAM) |
                    # Datasets shared with specific members
                    ((Dataset.permission == DatasetPermissionEnum.PARTIAL_TEAM) & 
                     Dataset.id.in_(
                         db.session.query(DatasetPermission.dataset_id).filter(
                             DatasetPermission.account_id == account.id,
                             DatasetPermission.has_permission == True
                         )
                     ))
                )
            )
        )
        
        # Get total count
        total = query.count()
        current_app.logger.info(f"Found {total} datasets for user")
        
        # Get paginated results
        datasets = query.order_by(Dataset.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            'data': datasets,
            'has_more': (offset + limit) < total,
            'total': total,
            'page': page,
            'limit': limit
        }


class EmailAppsApi(Resource):
    """API to get applications (agents) by user email"""
    
    app_fields = {
        'id': fields.String,
        'name': fields.String,
        'description': fields.String,
        'mode': fields.String,
        'icon': fields.String,
        'icon_background': fields.String,
        'icon_type': fields.String,
        'is_agent': fields.Boolean,
        'enable_site': fields.Boolean,
        'enable_api': fields.Boolean,
        'api_rpm': fields.Integer,
        'api_rph': fields.Integer,
        'status': fields.String,
        'created_by': fields.String,
        'created_at': TimestampField,
        'updated_by': fields.String,
        'updated_at': TimestampField,
        'is_demo': fields.Boolean,
        'is_public': fields.Boolean,
        'is_universal': fields.Boolean,
        'app_model_config_id': fields.String,
        'workflow_id': fields.String,
        'use_icon_as_answer_icon': fields.Boolean,
    }
    
    response_fields = {
        'data': fields.List(fields.Nested(app_fields)),
        'has_more': fields.Boolean,
        'total': fields.Integer,
        'page': fields.Integer,
        'limit': fields.Integer
    }
    
    @marshal_with(response_fields)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', type=str, required=True, location='args')
        parser.add_argument('page', type=int, default=1, location='args')
        parser.add_argument('limit', type=int, default=20, location='args')
        args = parser.parse_args()
        
        email = args['email']
        page = args['page']
        limit = args['limit']
        offset = (page - 1) * limit
        
        # Find the account
        account = db.session.query(Account).filter(Account.email == email).first()
        
        current_app.logger.info(f"Looking up account for email {email}: {account.id if account else 'Not found'}")
        
        if not account:
            return {
                'data': [],
                'has_more': False,
                'total': 0,
                'page': page,
                'limit': limit
            }
            
        # Get current tenant
        tenant_account = db.session.query(TenantAccountJoin).filter(
            TenantAccountJoin.account_id == account.id,
            TenantAccountJoin.current == True
        ).first()
        
        if not tenant_account:
            # Try to get any tenant
            tenant_account = db.session.query(TenantAccountJoin).filter(
                TenantAccountJoin.account_id == account.id
            ).first()
            
        current_app.logger.info(f"Found tenant for account: {tenant_account.tenant_id if tenant_account else 'Not found'}")
            
        if not tenant_account:
            return {
                'data': [],
                'has_more': False,
                'total': 0,
                'page': page,
                'limit': limit
            }
        
        # Get all apps created by the user or public apps
        base_query = db.session.query(App).filter(App.tenant_id == tenant_account.tenant_id)
        
        # Get installed apps for the tenant
        installed_app_ids = db.session.query(InstalledApp.app_id).filter(
            InstalledApp.tenant_id == tenant_account.tenant_id
        ).all()
        
        current_app.logger.info(f"Found {len(installed_app_ids) if installed_app_ids else 0} installed apps")
        
        if installed_app_ids:
            installed_app_ids = [app_id for (app_id,) in installed_app_ids]
            # 修改查询逻辑，使用 OR 条件
            query = base_query.filter(
                or_(
                    App.created_by == account.id,  # Apps created by the user
                    App.is_public == True,         # Public apps in the tenant
                    App.id.in_(installed_app_ids)  # Installed apps
                )
            )
        else:
            query = base_query.filter(
                or_(
                    App.created_by == account.id,  # Apps created by the user
                    App.is_public == True          # Public apps in the tenant
                )
            )
        
        # Get total count
        total = query.count()
        current_app.logger.info(f"Found total {total} apps")
        
        # Get paginated results
        apps = query.order_by(App.created_at.desc()).offset(offset).limit(limit).all()
        current_app.logger.info(f"Returning {len(apps)} apps for this page")
        
        return {
            'data': apps,
            'has_more': (offset + limit) < total,
            'total': total,
            'page': page,
            'limit': limit
        }


# Register API resources
api.add_resource(EmailDatasetsApi, '/workspaces/email/datasets')
api.add_resource(EmailAppsApi, '/workspaces/email/apps') 