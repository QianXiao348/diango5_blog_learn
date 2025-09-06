// static/js/pub_blog.js

$(document).ready(function() {
    // CSRF Token 获取函数
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const {createEditor, createToolbar} = window.wangEditor;
    const uploadImageUrl = "{% url 'blog:get_image_for_blog' %}";

    // WangEditor 配置
    const editorConfig = {
        placeholder: '请输入博客内容...',
        onChange(editor) {
            const html = editor.getHtml();
            $('#editor-content-textarea').val(html);
        },
        MENU_CONF: {
            uploadImage: {
                server: uploadImageUrl,
                fieldName: 'image_file',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
            }
        }
    };

    const editor = createEditor({
        selector: '#editor-container',
        html: '<p><br></p>',
        config: editorConfig,
        mode: 'default',
    });

    const toolbarConfig = {};
    const toolbar = createToolbar({
        editor,
        selector: '#toolbar-container',
        config: toolbarConfig,
        mode: 'default',
    });

    // 获取DOM元素
    const submitBtn = $('#submit-btn');
    const pubBlogForm = $('#pub-blog-form');
    const titleInput = $('#id-title');
    const categorySelect = $('#category-select');
    const contentTextarea = $('#editor-content-textarea');
    const publishMessageDiv = $('#publish-message');
    // ===============================================
    // 修正：从按钮的 data-redirect-url 属性中获取 URL 模板
    // ===============================================
    const blogDetailUrlTemplate = submitBtn.data('redirect-url');

    // 监听发布按钮的点击事件
    submitBtn.on('click', function(event) {
        event.preventDefault();

        // 清除之前的错误信息
        $('.form-error-message').text('');
        publishMessageDiv.empty();

        const title = titleInput.val();
        const categoryId = categorySelect.val();
        const content = contentTextarea.val();
        const csrfToken = getCookie('csrftoken');

        // 简单前端验证
        if (!title.trim()) {
            $('#title-error').text('标题不能为空！');
            return;
        }
        if (!content.trim()) {
            $('#content-error').text('内容不能为空！');
            return;
        }

        const postData = {
            'title': title,
            'category': categoryId,
            'content': content,
            'csrfmiddlewaretoken': csrfToken
        };

        // 发送 AJAX 请求到 Django 后端
        $.ajax({
            url: pubBlogForm.attr('action'),
            method: 'POST',
            data: postData,
            success: function(response, textStatus, jqXHR) {
                if (response.code === 200) {
                    alert('发布成功！');
                    const newBlogId = response.data.blog_id;
                    const redirectUrl = blogDetailUrlTemplate.replace("0", newBlogId);
                    window.location.href = redirectUrl;
                } else if (response.code === 202) {
                    const warningAlert = `<div class="alert alert-warning" role="alert">${response.msg}</div>`;
                    publishMessageDiv.html(warningAlert);
                    alert(response.msg);
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                const status = jqXHR.status;
                const response = jqXHR.responseJSON || { msg: '未知错误' };

                if (status === 400) {
                    alert('发布失败：内容违规');
                    if (response.errors) {
                        for (const key in response.errors) {
                            $(`#${key}-error`).text(response.errors[key].join(' '));
                        }
                    }
                } else if (status === 500) {
                    alert('服务器内部错误，请稍后再试。');
                    console.error('AJAX Error:', jqXHR);
                } else {
                    alert('网络错误或服务器异常：' + (response?.msg || '未知错误'));
                    console.error('AJAX 错误:', jqXHR.status, textStatus, errorThrown);
                }
            }
        });
    });
});