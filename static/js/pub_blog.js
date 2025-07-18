// static/js/pub_blog.js

window.onload = function () {
    const {createEditor, createToolbar} = window.wangEditor

    const editorConfig = {
        placeholder: '请输入博客内容...',
        onChange(editor) {
            const html = editor.getHtml()
            // console.log('editor content', html) // 调试用，可以保留或移除
            // 将编辑器内容同步到隐藏的 <textarea>
            document.getElementById('editor-content-textarea').value = html;
        },
        // 配置上传图片的接口
        MENU_CONF: {
            uploadImage: {
                server: uploadImageUrl, 
                fieldName: 'image_file', 
                headers: {
                    'X-CSRFToken': $("input[name='csrfmiddlewaretoken']").val(), // 从隐藏的 CSRF input 获取
                },
            }
        }
    }

    const editor = createEditor({
        selector: '#editor-container',
        html: '<p><br></p>', 
        config: editorConfig,
        mode: 'default', 
    })

    const toolbarConfig = {} 

    const toolbar = createToolbar({
        editor,
        selector: '#toolbar-container',
        config: toolbarConfig,
        mode: 'default', 
    })

    $("#submit-btn").click(function(event){
        event.preventDefault();

        // 在提交前，确保 wangEditor 的最新内容已同步到隐藏的 textarea (onChange 已经处理，这里可省略)
        // editorConfig.onChange(editor); // 如果 onChange 逻辑完整，这里不是必须

        let title = $("input[name='title']").val();
        let category = $("#category-select").val(); // <<-- 请再次确认 HTML 中的 ID 是 "category-select" 还是 "id_category"
        let content = $("#editor-content-textarea").val(); // <<-- 从隐藏的 textarea 获取内容
        let csrfmiddlewaretoken = $("input[name='csrfmiddlewaretoken']").val();

        $.ajax('/blog/pub', {
            method: 'POST',
            data: {title, category, content, csrfmiddlewaretoken},
            success: function(result){
                if(result['code'] == 200){
                    let blog_id = result['data']['blog_id']
                    const redirectUrlTemplate = $("#submit-btn").data('redirect-url'); 
                    window.location.href = redirectUrlTemplate.replace('0', blog_id);
                }else{
                    // 这里 alert result['message']，但后端返回的是 result['msg']
                    alert(result['msg']); 
                    console.error("发布博客失败:", result); 
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error("AJAX 发布请求失败:", textStatus, errorThrown, jqXHR.responseText);
                alert("网络请求失败，请稍后再试。");
            }
        })
    });
}