from django.apps import AppConfig


class MemberConfig(AppConfig):
    name = 'member'
    verbose_name = '会员积分'

    def ready(self):
        from django.contrib.auth.models import User
        from django.db.models.signals import post_save
        from django.dispatch import receiver
        from .models import Profile, PointRecord

        @receiver(post_save, sender=User)
        def create_user_profile(sender, instance, created, **kwargs):
            if created:
                Profile.objects.create(user=instance, points=100)
                PointRecord.objects.create(
                    user=instance, change_type="register",
                    delta=100, balance=100, note="新用户注册奖励",
                )
