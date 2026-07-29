# core/admin.py

from django.contrib import admin
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Organization, Club, Randonneur, Event, Result, Achievement
from core.models import MergeRequest


# El sistema define la accion personalizada para la fusion de perfiles
@admin.action(description="Fusionar perfiles seleccionados (Tratar duplicados)")
def fusionar_randonneurs_action(modeladmin, request, queryset):
    # El sistema exige seleccionar exactamente dos perfiles para proceder
    if queryset.count() != 2:
        modeladmin.message_user(
            request,
            "Error: Debe seleccionar exactamente dos perfiles para realizar una fusion.",
            messages.ERROR
        )
        return

    # Si se confirma la accion a traves del formulario intermedio
    if 'confirmar_fusion' in request.POST:
        master_id = request.POST.get('master_id')
        duplicate_id = request.POST.get('duplicate_id')

        if not master_id or not duplicate_id or master_id == duplicate_id:
            modeladmin.message_user(request, "Seleccion invalida.", messages.ERROR)
            return

        master = Randonneur.objects.get(pk=master_id)
        duplicate = Randonneur.objects.get(pk=duplicate_id)

        # 1. Transferencia de Logros (Achievements)
        duplicate.achievements.all().update(randonneur=master)

        # 2. Transferencia de Resultados (Results) controlando restricciones de unicidad (unique_together)
        for resultado_duplicado in duplicate.results.all():
            # Se comprueba si el perfil master ya tiene un resultado registrado para ese mismo evento
            resultado_existente = master.results.filter(event=resultado_duplicado.event).first()

            if resultado_existente:
                # Si ambos perfiles tienen resultado, el sistema conserva el de mejor tiempo o estatus FIN
                if resultado_duplicado.status == 'FIN' and resultado_existente.status != 'FIN':
                    resultado_existente.time = resultado_duplicado.time
                    resultado_existente.status = resultado_duplicado.status
                    resultado_existente.homologation_code = resultado_duplicado.homologation_code
                    resultado_existente.save()
                elif resultado_duplicado.status == 'FIN' and resultado_existente.status == 'FIN':
                    # Si ambos son finishers, se conserva el menor tiempo registrado
                    if resultado_duplicado.time and (
                            not resultado_existente.time or resultado_duplicado.time < resultado_existente.time):
                        resultado_existente.time = resultado_duplicado.time
                        resultado_existente.homologation_code = resultado_duplicado.homologation_code or resultado_existente.homologation_code
                        resultado_existente.save()
                # Se elimina el resultado duplicado sobrante para evitar violar la restriccion de unicidad
                resultado_duplicado.delete()
            else:
                # Si no hay conflicto, se reasigna el resultado directamente al perfil master
                resultado_duplicado.randonneur = master
                resultado_duplicado.save()

        # 3. Transferencia de Vinculacion de Usuario (User Claim)
        if not master.user and duplicate.user:
            master.user = duplicate.user
            master.is_claimed = True
            master.save()

            duplicate.user = None
            duplicate.is_claimed = False
            duplicate.save()

        # 4. Eliminacion segura del perfil duplicado
        nombre_eliminado = f"{duplicate.first_name} {duplicate.last_name}"
        duplicate.delete()

        modeladmin.message_user(
            request,
            f"Fusion completada. Se han transferido todos los resultados a {master.first_name} {master.last_name} y se ha eliminado el perfil duplicado de {nombre_eliminado}.",
            messages.SUCCESS
        )
        return HttpResponseRedirect(request.get_full_path())

    # Si todavia no se ha confirmado, se muestra la pantalla intermedia de seleccion
    perfil_a, perfil_b = queryset[0], queryset[1]
    context = {
        'perfil_a': perfil_a,
        'perfil_b': perfil_b,
        'opts': modeladmin.model._meta,
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }
    return render(request, 'admin/fusionar_confirmacion.html', context)


# Registro personalizado para el modelo Randonneur con su accion asociada
@admin.register(Randonneur)
class RandonneurAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'country', 'privacy_level', 'is_claimed', 'user')
    search_fields = ('first_name', 'last_name', 'user__username')
    list_filter = ('country', 'privacy_level', 'is_claimed')
    actions = [fusionar_randonneurs_action]



#conecta este modelo en la administración y le da Acción de Aprobación Masiva con un Clic.
#El admin selecciona las solicitudes de fusión pendientes y, al elegir la acción "Aprobar y ejecutar fusiones",
# el sistema reasociará los datos y eliminará el perfil duplicado.
@admin.register(MergeRequest)
class MergeRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'master', 'duplicate', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    actions = ['aprobar_fusiones_solicitadas']

    @admin.action(description="Aprobar y ejecutar las fusiones seleccionadas")
    def aprobar_fusiones_solicitadas(self, request, queryset):
        # El sistema filtra únicamente las solicitudes que esten pendientes
        pendientes = queryset.filter(status=MergeRequest.StatusChoices.PENDING)

        ejecutadas_count = 0
        for solicitud in pendientes:
            master = solicitud.master
            duplicate = solicitud.duplicate

            # Si alguno de los dos perfiles fue borrado previamente, saltamos la solicitud
            if not master or not duplicate:
                solicitud.status = MergeRequest.StatusChoices.REJECTED
                solicitud.save()
                continue

            # EJECUCIÓN DEL ALGORITMO DE FUSIÓN SEGURO:
            # 1. Reasociacion de Logros (Achievements)
            duplicate.achievements.all().update(randonneur=master)

            # 2. Reasociacion de Resultados (Results)
            for res_dup in duplicate.results.all():
                res_existente = master.results.filter(event=res_dup.event).first()
                if res_existente:
                    if res_dup.status == 'FIN' and res_existente.status != 'FIN':
                        res_existente.time = res_dup.time
                        res_existente.status = res_dup.status
                        res_existente.homologation_code = res_dup.homologation_code
                        res_existente.save()
                    elif res_dup.status == 'FIN' and res_existente.status == 'FIN':
                        if res_dup.time and (not res_existente.time or res_dup.time < res_existente.time):
                            res_existente.time = res_dup.time
                            res_existente.homologation_code = res_dup.homologation_code or res_existente.homologation_code
                            res_existente.save()
                    res_dup.delete()
                else:
                    res_dup.randonneur = master
                    res_dup.save()

            # 3. Guardado del estado en la solicitud de fusion antes de la eliminacion relacional
            solicitud.status = MergeRequest.StatusChoices.APPROVED
            solicitud.save()

            # 4. Eliminacion del perfil duplicado
            duplicate.delete()
            ejecutadas_count += 1

        self.message_user(
            request,
            f"Proceso finalizado. Se han ejecutado {ejecutadas_count} fusiones de perfiles de forma segura.",
            messages.SUCCESS
        )


# Registro directo para los demas modelos del sistema
admin.site.register(Organization)
admin.site.register(Club)
admin.site.register(Event)
admin.site.register(Result)
admin.site.register(Achievement)