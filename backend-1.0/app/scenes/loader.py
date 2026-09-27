import os
import importlib
import inspect
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session
from app.scenes.base import BaseScene
from app.models import Scene as DbScene

# 全局缓存已加载的文件场景插件
_plugins: Dict[str, BaseScene] = {}

class CustomScene(BaseScene):
    """
    动态自定义场景类。
    用户在桌面端创建、编辑并保存到数据库中的自定义场景，
    将在此类中动态实例化，并与系统内置的 Python 场景插件具有完全一致的运行行为和接口。
    """
    def __init__(
        self, 
        scene_id: str, 
        name: str, 
        description: str, 
        category: str, 
        default_params: Dict[str, Any], 
        system_prompt: str, 
        rag_metadata: List[Dict[str, Any]] = None
    ):
        self._scene_id = scene_id
        self._name = name
        self._description = description
        self._category = category
        self._default_params = default_params or {}
        self._system_prompt = system_prompt
        self._rag_metadata = rag_metadata or []

    @property
    def scene_id(self) -> str:
        return self._scene_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def category(self) -> str:
        return self._category

    @property
    def default_params(self) -> Dict[str, Any]:
        return self._default_params

    @property
    def system_prompt_template(self) -> str:
        return self._system_prompt

    def get_greeting(self, custom_params: Dict[str, Any] = None) -> str:
        params = self.default_params.copy()
        if custom_params:
            for k, v in custom_params.items():
                if k in params:
                    params[k] = v
                    
        # 允许用户在自定义场景参数中通过 greeting_template 指定欢迎语模板
        if "greeting_template" in params:
            try:
                return params["greeting_template"].format(**params)
            except Exception:
                pass
                
        char_name = params.get("character_name", "AI Assistant")
        return f"Hello! I am {char_name}, your practice partner for the '{self.name}' scene. What would you like to discuss today?"

    def get_evaluation_rules(self) -> str:
        # 允许用户通过参数配置场景专有的评估偏好规则
        if "evaluation_rules" in self.default_params:
            return self.default_params["evaluation_rules"]
        return super().get_evaluation_rules()


def load_file_plugins() -> Dict[str, BaseScene]:
    """
    只加载本地 Python 代码中定义的场景插件（包含静态兜底和动态目录扫描）。
    """
    global _plugins
    if _plugins:
        return _plugins

    # 1. 静态注册备份 (确保单文件 exe 下核心默认场景正常)
    try:
        from app.scenes.plugins.interview import InterviewScene
        from app.scenes.plugins.ordering import OrderingScene
        from app.scenes.plugins.meeting import MeetingScene
        
        for scene_class in [InterviewScene, OrderingScene, MeetingScene]:
            instance = scene_class()
            _plugins[instance.scene_id] = instance
    except ImportError as e:
        print(f"[场景加载器] 警告: 静态引入基础场景类失败: {e}")

    # 2. 动态目录扫描加载
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_dir = os.path.join(current_dir, "plugins")
        
        if os.path.exists(plugins_dir):
            for file in os.listdir(plugins_dir):
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = f"app.scenes.plugins.{file[:-3]}"
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, BaseScene) and obj is not BaseScene:
                                instance = obj()
                                _plugins[instance.scene_id] = instance
                    except Exception as inner_ex:
                        print(f"[场景加载器] 动态加载模块 {module_name} 异常: {inner_ex}")
    except Exception as e:
        print(f"[场景加载器] 扫描 plugins 目录异常: {e}")

    return _plugins


def load_scenes(db: Optional[Session] = None) -> Dict[str, BaseScene]:
    """
    统一加载所有可用场景。
    1. 首先载入本地静态/动态 Python 场景插件。
    2. 如果传入了数据库 Session，将进一步载入数据库中存储的自定义场景。
    3. 发生 ID 冲突时，优先保留 Python 插件（以保留其复杂校验规则），其他直接转化为 CustomScene 对象加载。
    """
    # 先加载本地代码场景插件
    file_scenes = load_file_plugins().copy()
    
    if not db:
        return file_scenes

    try:
        # 从数据库中拉取所有场景记录
        db_scenes = db.query(DbScene).all()
        for s in db_scenes:
            # 如果数据库中存在自定义场景（且未被 Python 插件硬编码实现）
            if s.id not in file_scenes:
                custom_instance = CustomScene(
                    scene_id=s.id,
                    name=s.name,
                    description=s.description,
                    category=s.category,
                    default_params=s.default_params,
                    system_prompt=s.system_prompt,
                    rag_metadata=s.rag_metadata
                )
                file_scenes[s.id] = custom_instance
    except Exception as e:
        print(f"[场景加载器] 从数据库加载自定义场景失败: {e}")
        
    return file_scenes


def get_scene(scene_id: str, db: Optional[Session] = None) -> Optional[BaseScene]:
    """
    获取单个场景实例（优先支持从数据库动态实时获取最新状态）。
    """
    # 如果有 db，针对数据库定义的场景，重新获取其实时内容，实现编辑即时生效
    if db:
        db_scene = db.query(DbScene).filter(DbScene.id == scene_id).first()
        if db_scene:
            # 校验是否属于代码插件
            file_scenes = load_file_plugins()
            if db_scene.id in file_scenes:
                return file_scenes[db_scene.id]
            
            # 返回最新的数据库状态实例化对象
            return CustomScene(
                scene_id=db_scene.id,
                name=db_scene.name,
                description=db_scene.description,
                category=db_scene.category,
                default_params=db_scene.default_params,
                system_prompt=db_scene.system_prompt,
                rag_metadata=db_scene.rag_metadata
            )
            
    # 回退到全局静态缓存加载
    return load_scenes(db).get(scene_id)
