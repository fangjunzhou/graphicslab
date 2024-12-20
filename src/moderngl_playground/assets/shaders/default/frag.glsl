#version 330

in vec4 vert_pos_view;
in vec4 vert_norm_world;
in vec4 vert_norm_view;

uniform mat4 mat_P;

out vec4 frag_color;

void main() {
  // Diffuse shading.
  // View space light direction.
  vec3 light_dir_view = vec3(0, 0, 1);
  // Diffuse light strength.
  float light_strength = clamp(dot(light_dir_view, vert_norm_view.xyz), 0, 1);
  frag_color = vec4(vec3(light_strength), 1);
}
