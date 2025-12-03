from nicegui import ui
import quark_api

# Global State
app_state = {
    "cookie": "",
    "user": None,
    "results": []
}


def main():
    # --- UI Components ---

    with ui.header().classes('bg-blue-600 items-center'):
        ui.icon('cloud', size='md', color='white')
        ui.label('QuarkHunter - Python Native').classes('text-lg font-bold text-white')

    # Content Area
    with ui.column().classes('w-full max-w-3xl mx-auto p-4 gap-4'):

        # 1. Cookie Manager
        with ui.card().classes('w-full'):
            ui.label('1. 配置 Cookie').classes('text-lg font-bold mb-2')

            with ui.row().classes('w-full items-center'):
                cookie_input = ui.textarea(placeholder='在此粘贴夸克 Cookie...').classes('w-full').props('rows=3')

            status_label = ui.label('').classes('text-sm')

            async def verify_cookie():
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
                    ui.notify('Cookie 验证成功', type='positive')
                else:
                    status_label.text = f'验证失败: {result}'
                    status_label.classes('text-red-500', remove='text-gray-500 text-green-500')
                    ui.notify('验证失败', type='negative')

            ui.button('验证并保存', on_click=verify_cookie).classes('mt-2 bg-blue-600 text-white')

        # 2. Search Area
        with ui.card().classes('w-full'):
            ui.label('2. 搜索资源').classes('text-lg font-bold mb-2')

            with ui.row().classes('w-full gap-2'):
                search_input = ui.input(placeholder='输入关键词...').classes('flex-grow').on('keydown.enter', lambda: perform_search())

                async def perform_search():
                    kw = search_input.value
                    if not kw: return

                    results_container.clear()
                    with results_container:
                        ui.spinner(size='lg')

                    # Run search in background
                    results = await io_bound(quark_api.search_resources, kw)
                    app_state["results"] = results

                    render_results()

                ui.button('搜索', on_click=perform_search).classes('bg-blue-600 text-white')

        # 3. Results List
        results_container = ui.column().classes('w-full gap-3')

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
                        # Icon
                        with ui.element('div').classes('w-16 h-16 bg-gray-100 flex items-center justify-center rounded'):
                            ui.label('Q').classes('font-bold text-xl text-blue-500')

                        # Info
                        with ui.column().classes('flex-grow'):
                            ui.label(res.get('note', '未命名')).classes('font-bold line-clamp-1')
                            ui.label(f"时间: {res.get('datetime', '')[:10]}").classes('text-xs text-gray-400')
                            ui.link('查看原链', res.get('url'), new_tab=True).classes('text-xs text-blue-400')

                        # Save Button
                        save_btn = ui.button('一键转存', on_click=lambda r=res: save_process(r)).classes('bg-blue-600 text-white')

                        # Store button reference to update it later if needed (complex in loop, simplified here)

        async def save_process(resource):
            if not app_state["cookie"]:
                ui.notify('请先配置 Cookie', type='warning')
                return

            url = resource.get('url', '')
            pwd_id = quark_api.extract_pwd_id(url)

            if not pwd_id:
                ui.notify('链接解析失败', type='negative')
                return

            ui.notify(f'正在处理: {resource.get("note")}', type='info')

            # Step 1: Check Validity
            valid, stoken_or_msg = await io_bound(quark_api.check_resource_validity, pwd_id, app_state["cookie"])

            if not valid:
                ui.notify(f'资源失效: {stoken_or_msg}', type='negative')
                return

            # Step 2: Save
            success, msg = await io_bound(quark_api.save_resource, pwd_id, stoken_or_msg, app_state["cookie"])

            if success:
                ui.notify('转存成功!', type='positive')
            else:
                ui.notify(f'转存失败: {msg}', type='negative')


# Helper to run blocking IO in executor
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

async def io_bound(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title='QuarkHunter Local')
