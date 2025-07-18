// static/js/edit_blog.js

document.addEventListener('DOMContentLoaded', function() {
    const { createEditor, createToolbar } = window.wangEditor;

    // 获取编辑器容器和工具栏容器
    const editorConfig = {
        placeholder: '请输入博客内容...',
        // 编辑器内容变化时的回调函数
        onChange(editor) {
            // 将编辑器内容同步到隐藏的textarea
            const html = editor.getHtml();
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
    };

    const editor = createEditor({
        selector: '#editor-container',
        html: document.getElementById('editor-content-textarea').value, // 从隐藏的textarea中获取初始内容
        config: editorConfig,
        mode: 'default', // 或 'simple'
    });
    const toolbar = createToolbar({
        editor,
        selector: '#toolbar-container',
        mode: 'default', // 或 'simple'
    });

    // --- 处理表单提交 ---
    const blogForm = document.getElementById('blog-form');
    const submitBtn = document.getElementById('submit-btn');

    if (submitBtn && blogForm) {
        submitBtn.addEventListener('click', function() {
            // 在提交前，确保wangEditor内容已经同步到隐藏的textarea
            // 实际上，onChange 已经处理了同步，但这里再调用一次确保最新
            editorConfig.onChange(editor); 

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const formData = new FormData(blogForm);

            fetch(blogForm.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.code === 200) {
                    alert(data.msg);
                    const redirectUrlTemplate = submitBtn.dataset.redirectUrl;
                    window.location.href = redirectUrlTemplate.replace('0', data.data.blog_id);

                } else {
                    alert('错误：' + data.msg + '\n' + JSON.stringify(data.errors || {}));
                    console.error('表单提交错误:', data.errors);
                }
            })
            .catch(error => {
                console.error('网络请求失败:', error);
                alert('网络请求失败，请稍后再试。');
            });
        });
    }
});