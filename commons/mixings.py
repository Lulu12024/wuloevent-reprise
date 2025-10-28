from .utils import custom_get_object_or_404 as get_object_or_404


class BaseModelMixin:

    def get_queryset(self):
        if not self.object_class:
            raise NotImplementedError
        return self.object_class.objects.all()

    def get_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        try:
            # return permission_classes depending on `action`
            return [get_permission_function(permission) for permission in
                    self.permission_classes_by_action[self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [get_permission_function(permission) for permission in self.permission_classes]

    def get_serializer_class(self):
        if not hasattr(self, 'serializer_classes_by_action'):
            return self.serializer_default_class
        try:
            # return serializer_class depending on `action`
            return self.serializer_classes_by_action[self.action]
        except KeyError:
            # action is not set return default serializer_class
            return self.serializer_default_class