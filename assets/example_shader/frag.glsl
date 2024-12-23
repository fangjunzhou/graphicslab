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
  vec3 light_dir_world = vec3(0, -1, 1);
  light_dir_world = normalize(light_dir_world);
  // Diffuse light strength.
  float light_strength = clamp(dot(light_dir_world, vert_norm_world.xyz), 0, 1);
  vec3 light_color = vec3(1, 1, 1);
  frag_color = vec4(light_colo * light_strength, 1);
}
