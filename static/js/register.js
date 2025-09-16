$(function () {
    // CSRF token 获取函数 (保持不变)
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

    // 绑定获取验证码按钮点击事件 (保持不变)
    function bindCaptchaBtnClick() {
        $("#captcha-btn").click(function (event) {
            let $this = $(this);
            let email = $("input[name='email']").val();

            if (!email) {
                alert("请先输入邮箱！");
                return;
            }

            $.ajax({
                url: '/auth/send_captcha?email=' + email,
                method: 'GET',
                success: function(result){
                    if(result['code'] == 200){
                        alert(result['message']);
                        let countdown = 60;
                        $this.prop('disabled', true);
                        $this.text(countdown + "s");

                        let timer = setInterval(function () {
                            if (countdown <= 0) {
                                $this.text('获取验证码');
                                $this.prop('disabled', false);
                                clearInterval(timer);
                            } else {
                                countdown--;
                                $this.text(countdown + "s");
                            }
                        }, 1000);

                    } else if (result['code'] === 429) {
                        alert(result['message']);
                    } else {
                        alert("发送失败：" + (result['message'] || "未知错误"));
                    }
                },
                error: function (jqXHR, textStatus, errorThrown){
                    alert("网络错误或服务器异常，请稍后重试。");
                    console.error("Captcha AJAX Error:", textStatus, errorThrown, jqXHR.responseText);
                }
            });
        });
    }

    bindCaptchaBtnClick();


    // ============== 处理表单AJAX提交 (主要修改在这里) ================
    $("#register-form").submit(function(event) {
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
                    alert(response.message);
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                } else {
                    // 验证失败
                    // 不再显示通用消息 '表单验证失败'

                    if (response.errors) {
                        let hasNonFieldErrors = false;
                        // 遍历后端返回的错误并显示
                        for (let fieldName in response.errors) {
                            if (response.errors.hasOwnProperty(fieldName)) {
                                let errorList = response.errors[fieldName];

                                if (fieldName === '__all__') { // 处理非字段错误
                                    $(`#error-__all__`).html(errorList.join('<br>')).show();
                                    hasNonFieldErrors = true;
                                } else {
                                    let $errorDiv = $(`#error-${fieldName}`);
                                    if ($errorDiv.length) {
                                        $errorDiv.text(errorList.join(' ')).show();
                                    }
                                }
                            }
                        }
                        // 如果没有 __all__ 错误，并且有其他字段错误，也可以考虑在此处显示一个较温和的提示
                        // 但你要求不显示红色提示，所以这里留空，只显示字段错误
                    }
                }
            },
            error: function(jqXHR, textStatus, errorThrown){
                alert("网络错误或服务器异常，请稍后重试。");
                console.error("Register AJAX Error:", textStatus, errorThrown, jqXHR.responseText);
                // 此时可以考虑显示一个通用的网络错误提示，但不是表单验证失败的提示
                $("#form-general-message").text('网络错误或服务器异常，请稍后重试。').show(); // 只有网络错误才显示
            }
        });
    });
});