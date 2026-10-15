{{/*
Return a release-scoped base name short enough to append resource suffixes.
*/}}
{{- define "logiflow.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 45 | trimSuffix "-" -}}
{{- end -}}

{{- define "logiflow.labels" -}}
app.kubernetes.io/name: {{ .name | quote }}
app.kubernetes.io/instance: {{ .root.Release.Name | quote }}
app.kubernetes.io/part-of: logiflow
app.kubernetes.io/managed-by: {{ .root.Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "logiflow.databaseHost" -}}
{{- printf "%s-postgres" (include "logiflow.fullname" .) -}}
{{- end -}}

{{- define "logiflow.backendService" -}}
{{- printf "%s-backend" (include "logiflow.fullname" .) -}}
{{- end -}}

{{- define "logiflow.frontendService" -}}
{{- printf "%s-frontend" (include "logiflow.fullname" .) -}}
{{- end -}}

{{- define "logiflow.configMap" -}}
{{- printf "%s-config" (include "logiflow.fullname" .) -}}
{{- end -}}

{{- define "logiflow.secret" -}}
{{- printf "%s-secret" (include "logiflow.fullname" .) -}}
{{- end -}}
