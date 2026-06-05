def log_api_call(
    api_type: str, 
    provider: str, 
    url: str, 
    model: str, 
    action: str, 
    status: str = "pending", 
    extra_info: str = None
):
    """
    格式化输出 API 调用日志提示，让用户/开发者在控制台一眼能够识别调用了哪个 API。
    支持 "pending"（开始）、"success"（成功）、"failed"（失败）三种状态。
    """
    border = "=" * 55
    if status == "pending":
        print(border)
        print("【API 调用提示 - 发起请求 >>>】")
        print(f"  * 调用类型  : {api_type}")
        print(f"  * 核心提供商: {provider}")
        print(f"  * 接口端点  : {url}")
        print(f"  * 请求模型  : {model}")
        print(f"  * 业务动作  : {action}")
        if extra_info:
            print(f"  * 附加参数  : {extra_info}")
        print(border)
    elif status == "success":
        print(border)
        print("【API 调用提示 - 请求成功 [OK]】")
        print(f"  * 调用类型  : {api_type}")
        print(f"  * 提供商/端点: {provider} ({url})")
        print(f"  * 模型版本  : {model}")
        if extra_info:
            print(f"  * 响应概要  : {extra_info}")
        print(border)
    elif status == "failed":
        print(border)
        print("【API 调用提示 - 调用异常 [FAIL]】")
        print(f"  * 调用类型  : {api_type}")
        print(f"  * 提供商/端点: {provider} ({url})")
        print(f"  * 异常原因  : {extra_info}")
        print(border)
