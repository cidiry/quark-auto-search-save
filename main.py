from contextlib import contextmanager

from nicegui import ui
import quark_api
import sys

sys.stdout = open("log.txt", "w", encoding="utf-8")
sys.stderr = open("err.txt", "w", encoding="utf-8")

app_state = {
    "cookie": "",
    "user": None,
    "results": []
}


def main():

    @contextmanager
    def disable(button: ui.button):
        button.disable()
        try:
            yield
        finally:
            button.enable()

    with ui.header().classes('bg-blue-600 items-center'):
        ui.icon('cloud', size='md', color='white')
        ui.label('夸克极速转存').classes('text-lg font-bold text-white')

        with ui.row().classes('ml-auto gap-x-4'):
            with ui.link(target='https://pan.quark.cn/', new_tab=True).classes('text-white'):
                ui.avatar("img:https://image.quark.cn/s/uae/g/3o/broccoli/resource/202404/d94d93e0-03a2-11ef-be4c-79ebae2e18ac.vnd.microsoft.icon", size='35px', color='white')
                ui.tooltip('跳转到夸克登录网址').classes('bg-gray-700 text-white')
            with ui.link(target='https://github.com/cidiry/quark-auto-search-save', new_tab=True).classes('text-white'):
                ui.avatar('img:https://github.githubassets.com/assets/pinned-octocat-093da3e6fa40.svg', size='35px', color='white')
                ui.tooltip('项目在 GitHub 上的开源地址').classes('bg-gray-700 text-white')

    # Content Area
    with ui.column().classes('w-full max-w-3xl mx-auto p-4 gap-4'):

        async def reset_cookie_ui(v_button: ui.button, i_button: ui.button):
            """重置 Cookie 输入和验证相关的 UI 状态"""
            # 1. 恢复验证按钮
            v_button.enable()

            # 2. 恢复导入按钮
            i_button.enable()

            # 3. 清除状态标签
            status_label.text = ''

            # 4. 重置程序状态
            app_state["cookie"] = ""
            app_state["user"] = None

        # 1. Cookie Manager
        async def show_button():
            current_visibility = cookie_input.visible
            cookie_input.set_visibility(not current_visibility)


        with ui.card().classes('w-full'):
            with ui.row().classes('w-full justify-between'):
                ui.label('1. 配置 Cookie').classes('text-lg font-bold mb-2')
                ui.button('隐藏/显示输入框', on_click=show_button).classes('mt-2 bg-blue-600 text-white')

            with ui.row().classes('w-full items-center'):
                cookie_input = ui.textarea(placeholder='在此粘贴夸克 Cookie...').classes('w-full').props('rows=3 clearable')

            status_label = ui.label('').classes('text-sm')

            async def verify_cookie(v_button: ui.button, i_button: ui.button):
                v_button.disable()
                i_button.disable()
                cookie = cookie_input.value
                if not cookie:
                    ui.notify('Cookie 不能为空', type='warning')
                    return

                status_label.text = '正在验证...'
                status_label.classes('text-gray-500', remove='text-red-500 text-green-500')

                valid, result = quark_api.check_user(cookie)

                if valid:
                    app_state["cookie"] = cookie
                    app_state["user"] = result
                    status_label.text = f'已连接: {result.get("nickname")}'
                    status_label.classes('text-green-500', remove='text-gray-500 text-red-500')
                    cookie_input.set_visibility(False)
                    ui.notify('Cookie 验证成功', type='positive')
                    return True
                else:
                    status_label.text = f'验证失败: {result}'
                    status_label.classes('text-red-500', remove='text-gray-500 text-green-500')
                    ui.notify('验证失败', type='negative')
                    v_button.enable()
                    i_button.enable()
                    return False

            async def import_cookie(i_button: ui.button, v_button: ui.button):
                i_button.disable()
                v_button.disable()
                from config import cookies
                cookie_input.set_value(cookies)
                v_state = await verify_cookie(v_button, i_button)
                if not v_state:
                    i_button.enable()
                    v_button.enable()

            with ui.row().classes('w-full justify-between'):
                v_s_b = ui.button('验证并保存', on_click=lambda e: verify_cookie(e.sender, i_c_b)).classes('mt-2 bg-blue-600 text-white')
                i_c_b = ui.button('导入配置文件中的cookie', on_click=lambda e: import_cookie(e.sender, v_s_b)).classes('mt-2 bg-blue-600 text-white')

            cookie_input.on_value_change(
                lambda e: reset_cookie_ui(v_s_b, i_c_b)
                if e.value == "" else None
            )
            cookie_input.on(
                'clear',
                lambda: reset_cookie_ui(v_s_b, i_c_b)
            )

        # 2. Search Area
        with ui.card().classes('w-full'):
            ui.label('2. 搜索资源').classes('text-lg font-bold mb-2')

            with ui.row().classes('w-full gap-2'):
                search_input = ui.input(placeholder='输入关键词...').classes('flex-grow').on('keydown.enter', lambda: perform_search())

                async def perform_search():
                    with disable(search_button):
                        kw = search_input.value
                        if not kw: return

                        results_container.clear()
                        with results_container:
                            ui.spinner(size='lg')

                        # Run search in background
                        results = await io_bound(quark_api.search_resources, kw)
                        app_state["results"] = results

                        render_results()

                search_button = ui.button('搜索', on_click=perform_search).classes('bg-blue-600 text-white')

        # 3. Results List
        results_container = ui.column().classes('w-full gap-3')

        async def save_process(resource, button: ui.button):
            button.disable()
            if not app_state["cookie"]:
                ui.notify('请先配置 Cookie', type='warning')
                button.enable()
                return

            url = resource.get('url', '')
            pwd_id = quark_api.extract_pwd_id(url)

            if not pwd_id:
                ui.notify('链接解析失败', type='negative')
                button.set_text("链接解析失败")
                button.props('color=red')
                return

            ui.notify(f'正在处理: {resource.get("note")}', type='info')

            # Step 1: Check Validity
            valid, stoken_or_msg = await io_bound(quark_api.check_resource_validity, pwd_id, app_state["cookie"])

            if not valid:
                ui.notify(f'资源失效: {stoken_or_msg}', type='negative')
                button.set_text("资源失效")
                button.props('color=red')
                return

            # Step 2: Save
            success, msg = await io_bound(quark_api.save_resource, pwd_id, stoken_or_msg, app_state["cookie"])

            if success:
                ui.notify('转存成功!', type='positive')
                button.set_text("已转存")
                button.props('color=green')
            else:
                ui.notify(f'转存失败: {msg}', type='negative')
                button.enable()

        def render_results():
            results_container.clear()
            results = app_state["results"]

            if not results:
                with results_container:
                    ui.label('暂无结果').classes('text-gray-400 w-full text-center')
                return

            with results_container:
                ui.label(f'找到 {len(results)} 个结果').classes('text-sm text-gray-500')

                for res in results:
                    with ui.card().classes('w-full flex-row gap-4 items-center'):
                        with ui.element('div').classes('w-16 h-16 bg-gray-100 flex items-center justify-center rounded'):
                            ui.label('Q').classes('font-bold text-xl text-blue-500')

                        with ui.column().classes('flex-grow'):
                            ui.label(res.get('note', '未命名')[:32]+'...' if len(res.get('note', '未命名')) > 32 else res.get('note', '未命名')).classes('font-bold line-clamp-1')
                            ui.label(f"时间: {res.get('datetime', '')[:10]}").classes('text-xs text-gray-400')
                            ui.link('查看文件详情', res.get('url'), new_tab=True).classes('text-xs text-blue-400')

                        save_btn = ui.button('一键转存').classes('bg-blue-600 text-white')
                        save_btn.on_click(lambda r=res, btn=save_btn: save_process(r, btn))





import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

async def io_bound(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

# ui.run(main, title='夸克网盘自动转存', reload=False, native=True)
ui.run(main, title='夸克网盘自动转存', reload=True)
