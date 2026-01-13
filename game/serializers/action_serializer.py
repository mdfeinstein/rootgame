from django.db import models
from django.apps import apps
from enum import Enum
import importlib

class ActionSerializer:
    @staticmethod
    def serialize_arg(arg):
        if isinstance(arg, models.Model):
            return {
                "_type": "model",
                "model": arg._meta.label, # 'game.Card'
                "pk": arg.pk
            }
        elif isinstance(arg, Enum):
            return {
                "_type": "enum",
                "module": arg.__class__.__module__,
                "class": arg.__class__.__name__,
                "name": arg.name
            }
        return arg

    @staticmethod
    def deserialize_arg(arg):
        if isinstance(arg, dict):
            if arg.get("_type") == "model":
                model_label = arg.get("model")
                pk = arg.get("pk")
                try:
                    Model = apps.get_model(model_label)
                    return Model.objects.get(pk=pk)
                except (LookupError, Model.DoesNotExist):
                    # Fallback or error? For now return None or raise
                    return None
            elif arg.get("_type") == "enum":
                module_name = arg.get("module")
                class_name = arg.get("class")
                member_name = arg.get("name")
                try:
                    module = importlib.import_module(module_name)
                    enum_class = getattr(module, class_name)
                    return enum_class[member_name]
                except (ImportError, AttributeError, KeyError):
                    return None
        return arg

    @classmethod
    def serialize_args(cls, args, kwargs):
        s_args = [cls.serialize_arg(a) for a in args]
        s_kwargs = {k: cls.serialize_arg(v) for k, v in kwargs.items()}
        return s_args, s_kwargs

    @classmethod
    def deserialize_args(cls, args, kwargs):
        d_args = [cls.deserialize_arg(a) for a in args]
        d_kwargs = {k: cls.deserialize_arg(v) for k, v in kwargs.items()}
        return d_args, d_kwargs
