#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 itemSize;
    float radiusPx;
    float depthPx;
    vec4 surfaceColor;
    vec4 shadowDark;
    vec4 shadowLight;
    vec4 accentColor;
    float stateActive;
};
float sdRoundRect(vec2 p, vec2 halfSize, float radius) {
    vec2 q = abs(p) - halfSize + vec2(radius);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - radius;
}
void main() {
    vec2 halfSize = max(itemSize * 0.5 - vec2(0.75), vec2(1.0));
    float radius = min(radiusPx, min(halfSize.x, halfSize.y));
    vec2 p = qt_TexCoord0 * itemSize - itemSize * 0.5;
    float sd = sdRoundRect(p, halfSize, radius);
    float coverage = smoothstep(1.1, -0.8, sd);
    float inside = max(-sd, 0.0);
    float eps = 0.8;
    float sx = sdRoundRect(p + vec2(eps, 0.0), halfSize, radius) - sdRoundRect(p - vec2(eps, 0.0), halfSize, radius);
    float sy = sdRoundRect(p + vec2(0.0, eps), halfSize, radius) - sdRoundRect(p - vec2(0.0, eps), halfSize, radius);
    vec2 normal = normalize(vec2(sx, sy) + vec2(0.0001));
    vec2 darkDirection = normalize(vec2(-1.0, -1.0));
    vec2 lightDirection = normalize(vec2(1.0, 1.0));
    float edge = exp(-inside / max(depthPx * 0.88, 1.0));
    float darkWeight = pow(max(dot(normal, darkDirection), 0.0), 1.18) * edge;
    float lightWeight = pow(max(dot(normal, lightDirection), 0.0), 1.18) * edge;
    vec3 rgb = surfaceColor.rgb;
    rgb *= 1.0 - shadowDark.a * darkWeight;
    rgb += shadowLight.rgb * lightWeight;
    float accentBand = exp(-inside / 1.85) * stateActive;
    rgb += accentColor.rgb * accentBand * 0.52;
    fragColor = vec4(rgb * coverage, coverage) * qt_Opacity;
}
