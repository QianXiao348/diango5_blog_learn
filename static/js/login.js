$(function () {
    // CSRF token 获取函数 (同 register.js)
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

    // ============== 处理登录表单AJAX提交 ================
    $("#login-form").submit(function(event) {
        event.preventDefault(); // 阻止默认的同步表单提交

        let $form = $(this);
        let formData = $form.serializeArray();
        let csrfToken = getCookie('csrftoken');

        // ==== 清除之前的错误信息 ====
        $("#form-general-message").hide().text(''); // 隐藏通用错误
        $("[id^='error-']").hide().text(''); // 隐藏所有字段错误


        $.ajax({
            url: $form.attr('action'),
            method: 'POST',
            data: formData,
            headers: {
                'X-CSRFToken': csrfToken
            },
            success: function(response){
                if(response.code === 200){
                    alert(response.message); // 可以替换为更友好的提示方式
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                } else {
                    // 验证失败
                    // 清除之前的通用消息，确保只显示当前错误
                    $("#form-general-message").hide().text('');

                    if (response.errors) {
                        for (let fieldName in response.errors) {
                            if (response.errors.hasOwnProperty(fieldName)) {
                                let errorList = response.errors[fieldName];

                                if (fieldName === '__all__') { // 处理非字段错误（如邮箱或密码不正确）
                                    $(`#error-__all__`).html(errorList.join('<br>')).show();
                                } else { // 处理特定字段错误
                                    let $errorDiv = $(`#error-${fieldName}`);
                                    if ($errorDiv.length) {
                                        $errorDiv.text(errorList.join(' ')).show();
                                    }
                                }
                            }
                        }
                    }
                    // 如果后端返回了 message 但没有 errors 字段，或者 errors 中没有 __all__ 错误
                    // 并且我们仍然想显示这个 message (作为某种通用提示)
                    else if (response.message) {
                         $("#form-general-message").text(response.message).show();
                    }
                }
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert("网络错误或服务器异常，请稍后重试。");
                console.error("Login AJAX Error:", textStatus, errorThrown, jqXHR.responseText);
                // 只有在真正的网络错误时才显示这个通用提示
                $("#form-general-message").text('网络错误或服务器异常，请稍后重试。').show();
            }
        });
    });
});