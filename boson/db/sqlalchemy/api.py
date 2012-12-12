# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import datetime

from boson import utils
from boson.exceptions import Duplicate

from boson.db import api
from boson.db import models as ref_models
from boson.db.sqlalchemy import models as sa_models
from boson.db.sqlalchemy import session as db_session
from boson.openstack.common import log as logging


LOG = logging.getLogger(__name__)

class API(api.API):
    def create_session(self, context):
        """
        Create a new session.  This will be stored on the user
        context, and can be used by the database to manage a single
        database connection.

        :param context: The current context for accessing the
                        database.
        """
        self.context = context
        session = db_session.get_session()
        self.context.session = session
        return session

    def begin(self, context):
        """
        Begin a transaction.

        :param context: The current context for accessing the
                        database.
        """

        pass

    def commit(self, context):
        """
        End a transaction, committing the changes to the database.

        :param context: The current context for accessing the
                        database.
        """
        self.context = context
        self.context.session.commit()
        

    def rollback(self, context):
        """
        End a transaction, rolling back the changes to the database.

        :param context: The current context for accessing the
                        database.
        """
        self.session = context.session
        self.session.rollback()
        

    def create_service(self, context, name, auth_fields):
        """
        Create a new service.  Raises a Duplicate exception in the
        event that the new service is a duplicate of an existing
        service.

        :param context: The current context for accessing the
                        database.
        :param name: The canonical name of the service, i.e., 'nova',
                     'glance', etc.
        :param auth_fields: A sequence listing the names of the fields
                            of authentication and authorization data
                            that the service passes to Boson to
                            uniquely identify the user.

        :returns: An instance of ``boson.db.models.Service``.
        """
        service = context.session.query(sa_models.Service).\
                                filter(sa_models.Service.name==name).first()
        try:
            if service is not None:
                LOG.error('Error in creating new service.Service of same'
                          'name %s already present'%name)
                raise Duplicate(klass=service)
        except Exception as err:
            LOG.exception(err)
        new_service = sa_models.Service(id=utils.generate_uuid(),
                                        name=name,
                                        created_at=datetime.datetime.now(),
                                        updated_at=datetime.datetime.now(),
                                        auth_fields=auth_fields)
        context.session.add(new_service)
        return new_service

    def get_service(self, context, id=None, name=None, hints=None):
        """
        Look up a specific service by name or by ID.

        :param context: The current context for accessing the
                        database.
        :param id: The ID of the service to look up.
        :param name: The name of the service to look up.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        Note: exactly one of ``id`` and ``name`` must be provided; if
        neither or both are provided, a TypeError will be raised.  If
        no matching service can be found, a KeyError will be raised.

        :returns: An instance of ``boson.db.models.Service``.
        """
        try:
            if id and name is not None:
                LOG.error('DB access error at service table.Values' 
                          'of both id and name are not allowed')
                raise TypeError
            elif id and name is None:
                LOG.error('DB access error at service table.Null values'
                          'of both id and name are not allowed')               
                raise TypeError
        except Exception as err:
            LOG.exception(err)
        service = context.session.query(sa_models.Service)        
        if id is not None:
            service = service.filter(sa_models.Service.id==id)
        else: 
            service = service.filter(sa_models.Service.name==name)                    
        service = service.first()
        if service is None:
                try:
                    LOG.error('No matching service for %s found'%(id or name)) 
                    raise KeyError(id or name)
                except Exception as err:
                    LOG.exception(err)            
        else:    
            return service       
       
    def get_services(self, context, hints=None):
        """
        Retrieve a list of all defined services.

        :param context: The current context for accessing the
                        database.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        :returns: A list of instances of ``boson.db.models.Service``.
        """
        pass
 
    def create_category(self, context, service, name, usage_fset, quota_fsets):
        """
        Create a new category on a service.  Raises a Duplicate
        exception in the event that the new category is a duplicate of
        an existing category for the service.

        :param context: The current context for accessing the
                        database.
        :param service: The service the category is for.  Can be
                        either a ``Service`` object or a UUID of an
                        existing service.
        :param name: The canonical name of the category.
        :param usage_fset: A sequence listing the names of the fields
                           of authentication and authorization data,
                           passed by the service to Boson, which are
                           to be used when looking up a ``Usage``
                           record.
        :param quota_fsets: A list of sequences of the names of the
                            fields of authentication and authorization
                            data, which are to be used when looking up
                            ``Quota`` records.  The list must be in
                            order from the most specific to the least
                            specific.  For instance, this list could
                            contain a set referencing the
                            ``tenant_id``, followed by a set
                            referencing the ``quota_class``, followed
                            by an empty set; in this example, a quota
                            applicable to the tenant would be used in
                            preference to one applicable to the quota
                            class, which would be used in preference
                            to the default quota.

        :returns: An instance of ``boson.db.models.Category``.
        """
        if isinstance(sa_models.Service, service):
            service = service.id        
        category = context.session.query(sa_models.Category).\
                                filter(sa_models.Category.name==name).\
                                filter(sa_models.Category.service_id==service).\
                                first()
        try:
            if category is not None:
                LOG.error('Error in creating new category.Category of same'
                      'name %s for service %s is already present'%(name,service))
                raise Duplicate(klass=category) 
        except Exception as err:
            LOG.exception(err)   
        new_category = sa_models.Category(id=utils.generate_uuid(),
                                          name=name,
                                          created_at=datetime.datetime.now(),
                                          updated_at=datetime.datetime.now(),
                                          service_id=service,
                                          usage_fset=usage_fset,
                                          quota_fsets=quota_fsets)
        context.session.add(new_category)
        return new_category

    def get_category(self, context, id=None, service=None, name=None,
                     hints=None):
        """
        Look up a specific category by id or by service and name.

        :param context: The current context for accessing the
                        database.
        :param id: The ID of the category to look up.
        :param service: The ``Service`` or service ID of the service
                        to look up the category in.
        :param name: The name of the category to look up.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        Note: either provide ``id`` or provide both ``service`` and
        ``name``.  If an invalid combination of arguments is provided,
        a TypeError will be raised.  If no matching category can be
        found, a KeyError will be raised.

        :returns: An instance of ``boson.db.models.Category``.
        """
        try:
            if id and name and service is not None:
                LOG.error('DB access error at categories table.'
                          'Values of id,service and name '
                          'altogether is not allowed')
                raise TypeError                    
            elif id and name and service is None:
                LOG.error('DB access error at categories table.'
                          'Null values of id,service and name '
                          'altogether is not allowed')               
                raise TypeError
        except Exception as err:
            LOG.exception(err)
        category = context.session.query(sa_models.Category)        
        if id is not None:
            category = category.filter(sa_models.Category.id==id)
        else: 
            category = category.filter(sa_models.Category.name==name).\
                                    filter(sa_models.Service.id==service.id)
        category = category.first()                                   
        if category is None:
            try:
                LOG.error("No matching category found for %s"%(name or id))
                raise KeyError(id or name)
            except Exception as err:
                LOG.exception(err)
        else:    
            return category
        

    def get_categories(self, context, service, hints=None):
        """
        Retrieve a list of all defined categories for a given service.

        :param context: The current context for accessing the
                        database.
        :param service: The ``Service`` or service ID of the service
                        to retrieve the categories for.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        :returns: A list of instances of ``boson.db.models.Category``.
        """

        pass

    def create_resource(self, context, service, category, name, parameters,
                        absolute=False):
        """
        Create a new resource on a service.  Raises a Duplicate
        exception in the event that the new resource is a duplicate of
        an existing resource for the service.

        :param context: The current context for accessing the
                        database.
        :param service: The service the resource is for.  Can be
                        either a ``Service`` object or a UUID of an
                        existing service.
        :param category: The category the resource is in.  Can be
                         either a ``Category`` object or a UUID of an
                         existing category.
        :param name: The canonical name of the resource.
        :param parameters: A sequence listing the names of the fields
                           of resource parameter data, passed by the
                           service to Boson, which are to be used when
                           looking up a ``Usage`` record.  Parameters
                           allow application of limits to resources
                           contained within other resources; that is,
                           if a resource has a limit of 5, using
                           parameter data would allow that limit to be
                           interpreted as 5 per parent resource.
        :param absolute: A boolean indicating whether the resource is
                         "absolute."  An absolute resource does not
                         maintain any usage records or allocate any
                         reservations.  Quota enforcement consists of
                         a simple numerical comparison of the
                         requested delta against the quota limit.
                         This is designed to accommodate ephemeral
                         resources, such as the number of files to
                         inject into a Nova instance on boot.

        :returns: An instance of ``boson.db.models.Resource``.
        """
        if isinstance(sa_models.Service,service):
            service = service.id
        if isinstance(sa_models.Category,category):
            category = category.id
        resource = context.session.query(sa_models.Resource).\
                                filter(sa_models.Resource.name==name).\
                                filter(sa_models.Resource.service_id==service).\
                                filter(sa_models.Resource.category_id==category).\
                                first()
        try:
            if resource is not None:
                LOG.error('Error in creating new resource.Resource of same'
                          'name %s for service %s and category %s is already'
                          'present'%(name,service,category))
                raise Duplicate(klass=resource) 
        except Exception as err:
            LOG.exception(err) 
        new_resource = sa_models.Resource(id=utils.generate_uuid(),
                                          name=name,
                                          parameters=parameters,
                                          created_at=datetime.datetime.now(),
                                          updated_at=datetime.datetime.now(),
                                          service_id=service,
                                          category_id=category,
                                          absolute=absolute)
        context.session.add(new_resource)
        return new_resource        

    def get_resource(self, context, id=None, service=None, name=None,
                     hints=None):
        """
        Look up a specific resource by id or by service and name.

        :param context: The current context for accessing the
                        database.
        :param id: The ID of the resource to look up.
        :param service: The ``Service`` or service ID of the service
                        to look up the resource in.
        :param name: The name of the resource to look up.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        Note: either provide ``id`` or provide both ``service`` and
        ``name``.  If an invalid combination of arguments is provided,
        a TypeError will be raised.  If no matching resource can be
        found, a KeyError will be raised.

        :returns: An instance of ``boson.db.models.Resource``.
        """
        if isinstance(sa_models.Service,service):
            service = service.id      
        try:
            if id and name and service is not None:
                LOG.error('DB access error at resource table.Values'
                          'of all id,name and service is not allowed ')
                raise TypeError
                    
            elif id and name and service is None:
                LOG.error('DB access error at resource table.Null values'
                          'of all id,name and service is not allowed ')               
                raise TypeError
        except Exception as err:
            LOG.exception(err)
        resource = context.session.query(sa_models.Resource)        
        if id is not None:
            resource = resource.filter(sa_models.Resource.id==id)
        else: 
            resource = resource.filter(sa_models.Resource.name==name).\
                              filter(sa_models.Resource.service_id==service)
        resource = resource.first()                         
        if resource is None:
            try:
                LOG.error('No matching resource found for requested %s'
                          'resource'%(name or id))
                raise KeyError(id or name)
            except Exception as err:
                LOG.exception(err)
        else:    
            return resource
        

    def get_resources(self, context, service, hints=None):
        """
        Retrieve a list of all defined resources for a given service.

        :param context: The current context for accessing the
                        database.
        :param service: The ``Service`` or service ID of the service
                        to retrieve the resources for.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        :returns: A list of instances of ``boson.db.models.Resource``.
        """
        pass

    def create_usage(self, context, resource, param_data, auth_data, used=0,
                     reserved=0, until_refresh=0, refresh_id=None):
        """
        Create a new usage for a given resource and user.  Raises a
        Duplicate exception in the event that the new usage is a
        duplicate of an existing usage.

        :param context: The current context for accessing the
                        database.
        :param resource: The resource the usage is for.  Can be either
                         a ``Resource`` object or a UUID of an
                         existing resource.
        :param param_data: Resource parameter data (a dictionary).
                           This is used to allow for usages of
                           resources which are children of another
                           resource, where the limit should apply only
                           within that parent resource.  This allows,
                           for example, a restriction on the number of
                           IP addresses for a given Nova instance,
                           without limiting the total number of IP
                           addresses that can be allocated.
        :param auth_data: Authentication and authorization data (a
                          dictionary).  This is used to match up a
                          usage with a particular user of the system.
        :param used: The amount of the resource currently in use.
                     Defaults to 0.
        :param reserved: The amount of the resource currently
                         reserved.  Note that negative reservations
                         are not counted here.  Defaults to 0.
        :param until_refresh: A counter which decrements each time the
                              usage record is used in a quota
                              computation.  When it reaches 0, the
                              usage record will be refreshed.
                              Defaults to 0.
        :param refresh_id: A UUID generated when the usage record
                           needs refreshing.  Refreshed usage
                           information will only be accepted if the
                           refresh has the same ID as stored in this
                           field.  Defaults to None.

        :returns: An instance of ``boson.db.models.Usage``.
        """
        if isinstance(sa_models.Resource,resource):
            resource = resource.id
        usage = context.session.query(sa_models.Usage).\
                              filter(sa_models.Usage.resource_id==resource).\
                              filter(sa_models.Usage.auth_data==auth_data).\
                              filter(sa_models.Usage.parameter_data==param_data).\
                              first()
        try:
            if usage is not None:
                LOG.error('Error in creating new usage.Usage for same'
                          'resource %s is already present'%(resource))
                raise Duplicate(klass=usage) 
        except Exception as err:
            LOG.exception(err) 
        new_usage = sa_models.Usage(id=utils.generate_uuid(),
                                    created_at=datetime.datetime.now(),
                                    updated_at=datetime.datetime.now(),
                                    parameter_data=param_data,
                                    auth_data=auth_data,
                                    resource_id=resource,
                                    until_refresh=until_refresh,
                                    refresh_id=refresh_id)
        context.session.add(new_usage)
        return new_usage        

    def get_usage(self, context, id=None, resource=None, param_data=None,
                  auth_data=None, hints=None):
        """
        Look up a specific usage by id or by resource, parameter data,
        and authentication and authorization data.

        :param context: The current context for accessing the
                        database.
        :param id: The ID of the usage to look up.
        :param resource: The ``Resource`` or resource ID of the
                         resource to look up the usage for.
        :param param_data: Resource parameter data (a dictionary).
        :param auth_data: Authentication and authorization data (a
                          dictionary).
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        Note: either provide ``id`` or provide all three of
        ``resource``, ``param_data``, and ``auth_data``.  If an
        invalid combination of arguments is provided, a TypeError will
        be raised.  If no matching resource can be found, a KeyError
        will be raised.

        :returns: An instance of ``boson.db.models.Usage``.
        """

        if isinstance(sa_models.Resource,resource):
            resource = resource.id
        try:  
            if id and resource and param_data and auth_data is not None:
                LOG.error('DB access error at usage table.Values for id,'
                          'resource,param_data and auth_data altogether'
                          'is not allowed')
                raise TypeError                    
            elif id and resource and param_data and auth_data is None:
                LOG.error('DB access error at usage table.Null values for'
                          'id,resource,param_data and auth_data altogether'
                          'is not allowed')
                raise TypeError
        except Exception as err:
            LOG.exception(err)
        usage = context.session.query(sa_models.Usage)        
        if id is not None:
            usage = usage.filter(sa_models.Usage.id==id)
        else: 
            usage = usage.filter(sa_models.Usage.resource_id==resource).\
                        filter(sa_models.Usage.parameter_data==param_data).\
                        filter(sa_models.Usage.auth_data==auth_data)
        usage = usage.first()                         
        if usage is None:
            try:
                LOG.error('No matching usage found for %s'
                           %(id or resource))
                raise KeyError(id or resource)
            except Exception as err:
                LOG.exception(err)
        else:    
            return usage

    def get_usages(self, context, resource=None, param_data=None,
                   auth_data=None, hints=None):
        """
        Retrieve a list of all defined usages.

        :param context: The current context for accessing the
                        database.
        :param resource: A ``Service`` or service ID to filter the
                         list of returned usages.
        :param param_data: Resource parameter data (a dictionary) to
                           filter the list of returned usages.  Should
                           be used in conjunction with the
                           ``resource`` filter.
        :param auth_data: Authentication and authorization data (a
                          dictionary) to filter the list of returned
                          usages.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        :returns: A list of instances of ``boson.db.models.Usage``.
        """

        pass

    def create_quota(self, context, resource, auth_data, limit=None):
        """
        Create a new quota for a given resource and user.  Raises a
        Duplicate exception in the event that the new quota is a
        duplicate of an existing quota.

        :param context: The current context for accessing the
                        database.
        :param resource: The resource the quota is for.  Can be either
                         a ``Resource`` object or a UUID of an
                         existing resource.
        :param auth_data: Authentication and authorization data (a
                          dictionary).  This is used to match up a
                          quota with a particular user of the system.
        :param limit: The limit on the number of the resource that the
                      user is permitted to allocate.  Defaults to
                      ``None`` (unlimited).

        :returns: An instance of ``boson.db.models.Quota``.
        """
        if isinstance(sa_models.Resource,resource):
            resource = resource.id
        quota = context.session.query(sa_models.Quota).\
                              filter(sa_models.Quota.resource_id==resource).\
                              filter(sa_models.Quota.auth_data==auth_data).\
                              first()
        try:
            if quota is not None:
                LOG.error('Error in creating new quota.Quota for same'
                          'resource %s is already present'%(resource))
                raise Duplicate(klass=quota) 
        except Exception as err:
            LOG.exception(err) 
              
        new_quota = sa_models.Quota(id=utils.generate_uuid(),
                                    created_at=datetime.datetime.now(),
                                    updated_at=datetime.datetime.now(),
                                    resorce_id=resource,
                                    auth_data=auth_data,
                                    limit=limit)
        context.session.add(new_quota)
        return new_quota        

    def get_quota(self, context, id=None, resource=None, auth_data=None,
                  hints=None):
        """
        Look up a specific quota by id or by resource and
        authentication and authorization data.

        :param context: The current context for accessing the
                        database.
        :param id: The ID of the quota to look up.
        :param resource: The ``Resource`` or resource ID of the
                         resource to look up the quota for.
        :param auth_data: Authentication and authorization data (a
                          dictionary).
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        Note: either provide ``id`` or both ``resource`` and
        ``auth_data``.  If an invalid combination of arguments is
        provided, a TypeError will be raised.  If no matching resource
        can be found, a KeyError will be raised.

        :returns: An instance of ``boson.db.models.Quota``.
        """

        if isinstance(sa_models.Resource,resource):
            resource = resource.id
        try:       
            if id and resource and auth_data is not None:
                LOG.error('DB access error at quota table.Values for id,'
                      'resource and auth_data altogether is not allowed')
                raise TypeError                    
            elif id and resource and auth_data is None:
                LOG.error('DB access error at quota table.Values for id,'
                      'resource and auth_data altogether is not allowed')
                raise TypeError
        except Exception as err:
            LOG.exception(err)
        quota = context.session.query(sa_models.Quota)        
        if id is not None:
            quota = quota.filter(sa_models.Quota.id==id)
        else: 
            quota = quota.filter(sa_models.Quota.resource_id==resource).\
                        filter(sa_models.Quota.auth_data==auth_data)
        quota = quota.first()                         
        if quota is None:
            try:
                LOG.error('No matching quota found for %s'%(id or resource))
                raise KeyError(id or resource)
            except Exception as err:
                LOG.exception(err)
        else:    
            return quota

    def get_quotas(self, context, resource=None, auth_data=None, hints=None):
        """
        Retrieve a list of all defined quotas.

        :param context: The current context for accessing the
                        database.
        :param resource: A ``Service`` or service ID to filter the
                         list of returned quotas.
        :param auth_data: Authentication and authorization data (a
                          dictionary) to filter the list of returned
                          quotas.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        :returns: A list of instances of ``boson.db.models.Quota``.
        """

        pass

    def create_reservation(self, context, expire):
        """
        Create a new reservation.

        :param context: The current context for accessing the
                        database.
        :param expire: A date and time at which the reservation will
                       expire.

        :returns: An instance of ``boson.db.models.Reservation``.
        """
        new_reservation = sa_models.Reservation(id=utils.generate_uuid(),
                                    created_at=datetime.datetime.now(),
                                    updated_at=datetime.datetime.now(),
                                    expire=expire)
        context.session.add(new_reservation)
        return new_reservation
        

    def reserve(self, context, reservation, resource, usage, delta):
        """
        Reserve a particular amount of a specific resource.

        :param context: The current context for accessing the
                        database.
        :param reservation: The reservation the item is reserved in.
                            Can be either a ``Reservation`` object or
                            a UUID of an existing reservation.
        :param resource: The resource the reserved item is for.  Can
                         be either a ``Resource`` object or a UUID of
                         an existing resource.
        :param usage: The usage record for the resource reservation.
                      Can be either a ``Usage`` object or a UUID of an
                      existing usage.
        :param delta: The amount of the resource to reserve.  May be
                      negative for deallocation.

        :returns: An instance of ``boson.db.models.ReservedItem``.
        """
        if isinstance(sa_models.Reservation, reservation):
            reservation = reservation.id
            
        if isinstance(sa_models.Resource, resource):
            resource = resource.id
            
        if isinstance(sa_models.Usage,usage):
            usage = usage.id

        new_reserved_items = sa_models.ReservedItem(id=utils.generate_uuid(),
                                    created_at=datetime.datetime.now(),
                                    updated_at=datetime.datetime.now(),
                                    reservation_id=reservation,
                                    resorce_id=resource,
                                    usage_id=usage,
                                    delta=delta)
        context.session.add(new_reserved_items)
        return new_reserved_items

    def get_reservation(self, context, id, hints=None):
        """
        Look up a specific reservation by id.

        :param context: The current context for accessing the
                        database.
        :param id: The ID of the reservation to look up.
        :param hints: An optional list of hints indicating which
                      attributes of the model will be required by the
                      calling code.  Only those attributes which
                      reference other fields need be listed, although
                      it is not an error to list other fields.  It is
                      also permissible to indicate deeper levels of
                      access by separating attributes with periods.
                      (In the case of reference fields which are
                      represented as lists, there is no need to use
                      square brackets.)

        Note: if no matching reservation can be found, a KeyError will
        be raised.

        :returns: An instance of ``boson.db.models.Reservation``.
        """

        reservation = context.session.query(sa_models.Reservation)
        
        if id is not None:
            reservation = reservation.filter(sa_models.Reservation.id==id)
            reservation = reservation.first()
        
        if reservation is not None:
            try:
                LOG.error("No matching reservation found for %s id"%(id))
                raise KeyError(id)
            except Exception as err:
                LOG.exception(err) 
        return reservation

    def expire_reservations(self, context):
        """
        Rolls back all expired reservations.

        :param context: The current context for accessing the
                        database.
        """

        pass

    def _lazy_get(self, context, base_obj, field, hints, klass):
        """
        Called to obtain the given field from the base database
        object.  Used to resolve cross-references to other database
        objects.

        :param context: The current context for accessing the
                        database.
        :param base_obj: The underlying database object to retrieve
                         the field from.
        :param field: The name of the field to retrieve.
        :param hints: An object expressing hints to the underlying
                      database system.  This object will have been
                      passed to the model class constructor by the
                      underlying database system.
        :param klass: The model class that is expected to be returned
                      from ``lazy_get()``.

        :returns: An instance of ``klass``.
        """

        pass

    def _lazy_get_list(self, context, base_obj, field, hints, klass):
        """
        Called to obtain the given field from the base database
        object.  Used to resolve cross-references to lists of other
        database objects.

        :param context: The current context for accessing the
                        database.
        :param base_obj: The underlying database object to retrieve
                         the field from.
        :param field: The name of the field to retrieve.
        :param hints: An object expressing hints to the underlying
                      database system.  This object will have been
                      passed to the model class constructor by the
                      underlying database system.
        :param klass: The model class that is expected to be returned
                      from ``lazy_get_list()``.

        :returns: A list of instances of ``klass``.
        """

        pass

    def _save(self, context, base_obj):
        """
        Called to update the underlying database with the changes made
        to a base database object.

        :param context: The current context for accessing the
                        database.
        :param base_obj: The underlying database object to save to the
                         database.
        """
        #Here I have assumed that base_obj is the modified db object
        context.session.commit()
        

    def _delete(self, context, base_obj):
        """
        Called to delete the underlying base database object from the
        database.

        :param context: The current context for accessing the
                        database.
        :param base_obj: The underlying database object to delete from
                         the database.
        """

        context.session.delete(base_obj)

