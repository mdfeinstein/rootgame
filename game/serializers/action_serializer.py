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
                "class": arg.__class__.__qualname__,
                "name": arg.name
            }
        elif isinstance(arg, (list, tuple)):
           return [ActionSerializer.serialize_arg(item) for item in arg]
        elif isinstance(arg, dict):
           return {k: ActionSerializer.serialize_arg(v) for k, v in arg.items()}
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
                    # Handle nested classes (e.g. DecreeEntry.Column)
                    parts = class_name.split('.')
                    obj = module
                    for part in parts:
                        obj = getattr(obj, part)
                    enum_class = obj
                    return enum_class[member_name]
                except (ImportError, AttributeError, KeyError, TypeError):
                    # Try finding the class in top level if split failed or something weird happened
                    # But for now, just return None if it fails
                    print(f"Failed to deserialize enum: {module_name}.{class_name}.{member_name}")
                    return None
        elif isinstance(arg, list):
            return [ActionSerializer.deserialize_arg(item) for item in arg]
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
